import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List, Dict
import io
from utils.validators import validate_file
from utils.embed_builder import create_document_embed
from app import app, db
from models.document import Document
import asyncio
from functools import partial

logger = logging.getLogger(__name__)

# Global document storage to persist state
document_storage: Dict[str, List[Dict]] = {}

async def save_documents_to_db(documents, name, author_id, author_name):
    """
    Save documents to database in a separate function.
    Returns True if successful, False otherwise.
    """
    try:
        logger.debug(f"Attempting to save {len(documents)} documents with name: {name}")
        with app.app_context():
            logger.debug("Starting database transaction")
            for doc in documents:
                db_doc = Document(
                    name=name,
                    content=doc['content'],
                    context=doc['context'],
                    author_id=author_id,
                    author_name=author_name
                )
                db.session.add(db_doc)
                logger.debug(f"Added document to session: {db_doc.name}")

            logger.debug("Committing transaction")
            db.session.commit()
            logger.debug("Transaction committed successfully")
            return True
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        with app.app_context():
            db.session.rollback()
        return False

class DocumentTypeSelect(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.context = None
        self.modal = None
        self.file_content = None

    @discord.ui.select(
        placeholder="Seleziona il tipo di documento",
        options=[
            discord.SelectOption(label="CPI", description="Certificato Prevenzione Incendi"),
            discord.SelectOption(label="HARCP", description="Hazard Analysis and Critical Control Points"),
            discord.SelectOption(label="Lic.Alcohol", description="Licenza Alcol"),
            discord.SelectOption(label="Mod. FoodTruck", description="Modulo FoodTruck"),
            discord.SelectOption(label="Lic.Security", description="Licenza Sicurezza"),
            discord.SelectOption(label="Other", description="Altro tipo di documento")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        logger.debug("Document type selected")
        self.context = select.values[0]
        self.modal = DocumentUploadModal(self.context)
        await interaction.response.send_modal(self.modal)

class DocumentUploadModal(discord.ui.Modal, title="Carica Documento"):
    def __init__(self, context_type: str):
        super().__init__(title="Carica Documento")
        self.context_type = context_type

    file_input = discord.ui.TextInput(
        label="Contenuto del Documento",
        placeholder="Incolla qui il contenuto del documento...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not validate_file(self.file_input.value):
            await interaction.response.send_message(
                "Contenuto del documento non valido. Riprova.",
                ephemeral=True
            )
            return

        self.file_content = self.file_input.value.encode()
        self.context_text = self.context_type
        await interaction.response.send_message(
            f"Documento di tipo {self.context_type} pronto per il caricamento!",
            ephemeral=True
        )

class DocumentUploadView(discord.ui.View):
    def __init__(self, name: str, user_id: str, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.name = name
        self.storage_key = f"{name}_{user_id}"  # Make storage key unique per user
        if self.storage_key not in document_storage:
            document_storage[self.storage_key] = []
        logger.debug(f"Created new view with storage key: {self.storage_key}, current docs: {len(self.documents)}")

    @property
    def documents(self):
        docs = document_storage.get(self.storage_key, [])
        logger.debug(f"Retrieving documents for key {self.storage_key}, count: {len(docs)}")
        return docs

    @discord.ui.button(label="Allega Documento", style=discord.ButtonStyle.primary)
    async def attach_document(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug(f"Attach document button clicked for storage key: {self.storage_key}")
        view = DocumentTypeSelect()
        await interaction.response.send_message("Seleziona il tipo di documento:", view=view, ephemeral=True)

        try:
            await view.wait()
            if not view.modal:
                logger.warning("No modal created after selection")
                return

            await view.modal.wait()
            if not hasattr(view.modal, 'file_content'):
                logger.warning("No file content after modal submission")
                return

            # Add document to the storage
            document_storage[self.storage_key].append({
                'content': view.modal.file_content,
                'context': view.modal.context_text
            })
            logger.debug(f"Added document. Total documents: {len(self.documents)}")

            # Update button label
            button.label = f"Documenti Allegati: {len(self.documents)}"

            try:
                await interaction.message.edit(view=self)
                logger.debug("View updated successfully")
            except Exception as e:
                logger.error(f"Failed to update view: {e}")
                await interaction.followup.send(
                    f"Documento allegato con successo! (Totale: {len(self.documents)})",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in document attachment process: {e}", exc_info=True)
            await interaction.followup.send(
                "Si è verificato un errore durante l'allegamento del documento.",
                ephemeral=True
            )

    @discord.ui.button(label="Invia", style=discord.ButtonStyle.green)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug(f"Submit button clicked. Documents count: {len(self.documents)}")

        if not self.documents:
            logger.warning(f"No documents found in storage for key: {self.storage_key}")
            await interaction.response.send_message(
                "Per favore allega almeno un documento prima!",
                ephemeral=True
            )
            return

        try:
            # First defer the response to prevent timeout
            logger.debug("Deferring response")
            await interaction.response.defer(ephemeral=True)

            files = []
            embeds = []

            for idx, doc in enumerate(self.documents, 1):
                # Create Discord file and embed
                file = discord.File(
                    io.BytesIO(doc['content']),
                    filename=f"documento_{idx}.txt"
                )
                files.append(file)

                embed = create_document_embed(
                    author=interaction.user,
                    context=doc['context'],
                    index=idx,
                    name=self.name
                )
                embeds.append(embed)

            # Send documents to channel first
            logger.debug("Sending documents to channel")
            message = await interaction.channel.send(
                embeds=embeds,
                files=files
            )

            # Save to database using the function
            logger.debug("Starting database save operation")
            success = await save_documents_to_db(
                self.documents,
                self.name,
                str(interaction.user.id),
                interaction.user.display_name
            )

            if not success:
                logger.error("Database save operation failed")
                if message:
                    await message.delete()
                await interaction.followup.send(
                    "Errore durante il salvataggio dei documenti nel database.",
                    ephemeral=True
                )
                return

            # Clean up storage after successful save
            if self.storage_key in document_storage:
                del document_storage[self.storage_key]
                logger.debug(f"Cleaned up storage for key: {self.storage_key}")

            # Send success message using followup
            logger.debug("Sending success message")
            await interaction.followup.send(
                "Documenti caricati con successo!",
                ephemeral=True
            )

            self.stop()

        except Exception as e:
            logger.error(f"Error in submit: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "Errore durante il caricamento dei documenti. Riprova.",
                    ephemeral=True
                )
            except discord.errors.InteractionNotFound:
                logger.error("Could not send error message - interaction expired")

class DocumentHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="documenti",
        description="Carica più documenti con un nome specifico"
    )
    @app_commands.describe(
        nome="Nome per identificare questi documenti"
    )
    @app_commands.checks.has_permissions(attach_files=True)
    async def documents(self, interaction: discord.Interaction, nome: str):
        try:
            view = DocumentUploadView(name=nome, user_id=str(interaction.user.id))
            await interaction.response.send_message(
                f"Caricamento documenti per '{nome}'.\nUsa i pulsanti qui sotto per caricare i tuoi documenti:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in documents command: {e}")
            await interaction.response.send_message(
                "Si è verificato un errore durante l'elaborazione della richiesta.",
                ephemeral=True
            )

    @documents.error
    async def documents_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Non hai i permessi per caricare documenti!",
                ephemeral=True
            )
        else:
            logger.error(f"Unexpected error in documents command: {error}")
            await interaction.response.send_message(
                "Si è verificato un errore imprevisto. Riprova più tardi.",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DocumentHandler(bot))