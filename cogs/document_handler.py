import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List
import io
from utils.validators import validate_file
from utils.embed_builder import create_document_embed
from app import app, db
from models.document import Document

logger = logging.getLogger(__name__)

class DocumentUploadView(discord.ui.View):
    def __init__(self, name: str, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.documents = []  # List to store multiple documents
        self.name = name

    @discord.ui.button(label="Allega Documento", style=discord.ButtonStyle.primary)
    async def attach_document(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DocumentUploadModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.file_content and modal.context_text:
            self.documents.append({
                'content': modal.file_content,
                'context': modal.context_text
            })

            # Update button label to show document count
            button.label = f"Documenti Allegati: {len(self.documents)}"

            # Use edit_original_response instead of edit_original_message
            try:
                await interaction.message.edit(view=self)
            except Exception as e:
                logger.error(f"Error updating view: {e}")
                # If edit fails, at least confirm to the user
                await interaction.followup.send(
                    "Documento allegato con successo!",
                    ephemeral=True
                )

    @discord.ui.button(label="Invia", style=discord.ButtonStyle.green)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug("Submit button clicked")

        if not self.documents:
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

            # Use Flask app context for database operations
            with app.app_context():
                try:
                    logger.debug("Adding documents to database")
                    # Add all documents to the database
                    for doc in self.documents:
                        db_doc = Document(
                            name=self.name,
                            content=doc['content'],
                            context=doc['context'],
                            author_id=str(interaction.user.id),
                            author_name=interaction.user.display_name
                        )
                        db.session.add(db_doc)

                    logger.debug("Committing to database")
                    db.session.commit()
                    logger.debug("Database commit successful")
                except Exception as e:
                    logger.error(f"Database error: {e}", exc_info=True)
                    db.session.rollback()
                    if message:
                        await message.delete()
                    await interaction.followup.send(
                        "Errore durante il salvataggio dei documenti nel database.",
                        ephemeral=True
                    )
                    return

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

class DocumentUploadModal(discord.ui.Modal, title="Carica Documento"):
    context_input = discord.ui.TextInput(
        label="Contesto",
        placeholder="Fornisci il contesto per questo documento...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    file_input = discord.ui.TextInput(
        label="Contenuto del Documento",
        placeholder="Incolla qui il contenuto del documento...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.context_text = self.context_input.value

        if not validate_file(self.file_input.value):
            await interaction.response.send_message(
                "Contenuto del documento non valido. Riprova.",
                ephemeral=True
            )
            return

        self.file_content = self.file_input.value.encode()
        await interaction.response.send_message(
            "Documento pronto per il caricamento!",
            ephemeral=True
        )

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
            view = DocumentUploadView(name=nome)
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

    @app_commands.command(
        name="attivita",
        description="Mostra tutti i documenti per un nome specifico"
    )
    @app_commands.describe(
        nome="Nome dei documenti da cercare"
    )
    async def activities(self, interaction: discord.Interaction, nome: str):
        try:
            with app.app_context():
                # Query documents from database
                documents = Document.query.filter_by(name=nome).all()

            if not documents:
                await interaction.response.send_message(
                    f"Nessun documento trovato per '{nome}'.",
                    ephemeral=True
                )
                return

            # Send documents
            files = []
            embeds = []

            for idx, doc in enumerate(documents, 1):
                file = discord.File(
                    io.BytesIO(doc.content),
                    filename=f"documento_{idx}.txt"
                )
                files.append(file)

                embed = create_document_embed(
                    author=interaction.user,
                    context=doc.context,
                    index=idx,
                    name=nome
                )
                embeds.append(embed)

            await interaction.response.send_message(
                f"Documenti trovati per '{nome}':",
                embeds=embeds,
                files=files
            )

        except Exception as e:
            logger.error(f"Error in activities command: {e}")
            await interaction.response.send_message(
                "Si è verificato un errore durante la ricerca dei documenti.",
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