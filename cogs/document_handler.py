import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
import io
from utils.validators import validate_file
from utils.embed_builder import create_document_embed

logger = logging.getLogger(__name__)

class DocumentUploadView(discord.ui.View):
    def __init__(self, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.context_text = None
        self.file = None
        
    @discord.ui.button(label="Attach Document", style=discord.ButtonStyle.primary)
    async def attach_document(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DocumentUploadModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        if modal.file_content and modal.context_text:
            self.context_text = modal.context_text
            self.file = modal.file_content
            button.disabled = True
            button.label = "Document Attached"
            button.style = discord.ButtonStyle.success
            
            await interaction.edit_original_response(view=self)

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.green)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.file or not self.context_text:
            await interaction.response.send_message(
                "Please attach a document and provide context first!",
                ephemeral=True
            )
            return

        try:
            # Create file object from the stored content
            file = discord.File(
                io.BytesIO(self.file),
                filename="document.txt"
            )
            
            # Create and send embed with the document
            embed = create_document_embed(
                author=interaction.user,
                context=self.context_text
            )
            
            await interaction.channel.send(
                embed=embed,
                file=file
            )
            
            await interaction.response.send_message(
                "Document uploaded successfully!",
                ephemeral=True
            )
            self.stop()
            
        except Exception as e:
            logger.error(f"Error submitting document: {e}")
            await interaction.response.send_message(
                "Failed to submit document. Please try again.",
                ephemeral=True
            )

class DocumentUploadModal(discord.ui.Modal, title="Upload Document"):
    context_input = discord.ui.TextInput(
        label="Context",
        placeholder="Provide context for this document...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    file_input = discord.ui.TextInput(
        label="Document Content",
        placeholder="Paste your document content here...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        self.context_text = self.context_input.value
        
        # Validate file content
        if not validate_file(self.file_input.value):
            await interaction.response.send_message(
                "Invalid file content. Please try again.",
                ephemeral=True
            )
            return
            
        self.file_content = self.file_input.value.encode()
        await interaction.response.send_message(
            "Document prepared for upload!",
            ephemeral=True
        )

class DocumentHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="documents",
        description="Upload a document with context"
    )
    @app_commands.checks.has_permissions(attach_files=True)
    async def documents(self, interaction: discord.Interaction):
        try:
            view = DocumentUploadView()
            await interaction.response.send_message(
                "Use the buttons below to upload your document:",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error in documents command: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your request.",
                ephemeral=True
            )

    @documents.error
    async def documents_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to upload documents!",
                ephemeral=True
            )
        else:
            logger.error(f"Unexpected error in documents command: {error}")
            await interaction.response.send_message(
                "An unexpected error occurred. Please try again later.",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DocumentHandler(bot))
