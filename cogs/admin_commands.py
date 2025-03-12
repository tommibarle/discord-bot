import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timedelta, timezone
from app import app, db
from models.document import Document
from models.activity import Inspection, Sanction
import io

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ispezione",
        description="Carica un documento di ispezione per un'attività"
    )
    @app_commands.describe(
        activity="Nome dell'attività da ispezionare",
        attachment="File dell'ispezione"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def ispezione(
        self,
        interaction: discord.Interaction,
        activity: str,
        attachment: discord.Attachment
    ):
        try:
            logger.debug(f"Starting inspection upload for activity: {activity}")
            logger.debug(f"Attachment details - Name: {attachment.filename}, Size: {attachment.size}")

            # First defer the response to prevent timeout
            await interaction.response.defer()

            # Download the attachment
            content = await attachment.read()
            logger.debug("Successfully read attachment content")

            # Create inspection record
            with app.app_context():
                logger.debug(f"Creating inspection record for {activity}")
                inspection = Inspection(
                    activity_name=activity,
                    content=content,
                    author_id=str(interaction.user.id),
                    author_name=interaction.user.display_name
                )
                db.session.add(inspection)
                db.session.commit()
                logger.debug("Inspection record created successfully")

            # Create a more descriptive filename
            filename = f"ispezione_{activity}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
            filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            logger.debug(f"Generated filename: {filename}")

            # Send confirmation with the file
            file = discord.File(
                io.BytesIO(content),
                filename=filename
            )

            embed = discord.Embed(
                title=f"Ispezione per {activity}",
                description="Ispezione caricata con successo",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.followup.send(
                embed=embed,
                file=file
            )
            logger.debug("Inspection response sent successfully")

        except Exception as e:
            logger.error(f"Error in inspection command: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Si è verificato un errore durante il caricamento dell'ispezione.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Si è verificato un errore durante il caricamento dell'ispezione.",
                    ephemeral=True
                )

    @app_commands.command(
        name="sanzione",
        description="Applica una sanzione a un'attività"
    )
    @app_commands.describe(
        activity="Nome dell'attività da sanzionare",
        reason="Motivo della sanzione",
        sanction="Dettagli della sanzione"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def sanzione(
        self,
        interaction: discord.Interaction,
        activity: str,
        reason: str,
        sanction: str
    ):
        try:
            with app.app_context():
                sanction_record = Sanction(
                    activity_name=activity,
                    reason=reason,
                    sanction_text=sanction,
                    author_id=str(interaction.user.id),
                    author_name=interaction.user.display_name
                )
                db.session.add(sanction_record)
                db.session.commit()

            embed = discord.Embed(
                title=f"Sanzione per {activity}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Motivo", value=reason, inline=False)
            embed.add_field(name="Sanzione", value=sanction, inline=False)
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in sanction command: {e}", exc_info=True)
            await interaction.response.send_message(
                "Si è verificato un errore durante l'applicazione della sanzione.",
                ephemeral=True
            )

    @app_commands.command(
        name="stipendio",
        description="Calcola lo stipendio di un utente basato sui documenti inseriti"
    )
    @app_commands.describe(
        user="L'utente di cui calcolare lo stipendio"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def stipendio(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        try:
            # Calculate date range using timezone-aware datetime
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)
            logger.debug(f"Calculating salary for {user.display_name} between {start_date} and {end_date}")

            with app.app_context():
                # Count documents with proper date filtering
                regular_docs = Document.query.filter(
                    Document.author_id == str(user.id),
                    Document.created_at >= start_date,
                    Document.created_at <= end_date
                ).count()
                logger.debug(f"Found {regular_docs} regular documents for user {user.display_name}")

                inspections = Inspection.query.filter(
                    Inspection.author_id == str(user.id),
                    Inspection.created_at >= start_date,
                    Inspection.created_at <= end_date
                ).count()
                logger.debug(f"Found {inspections} inspections for user {user.display_name}")

            # Calculate salary
            regular_salary = regular_docs * 2000
            inspection_salary = inspections * 3000
            total_salary = regular_salary + inspection_salary

            logger.debug(f"Calculated salary for {user.display_name}:")
            logger.debug(f"Regular docs ({regular_docs}): €{regular_salary:,}")
            logger.debug(f"Inspections ({inspections}): €{inspection_salary:,}")
            logger.debug(f"Total: €{total_salary:,}")

            embed = discord.Embed(
                title=f"Calcolo Stipendio per {user.display_name}",
                description=f"Periodo: ultimi 7 giorni",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Documenti Normali",
                value=f"{regular_docs} documenti (€{regular_salary:,})",
                inline=False
            )
            embed.add_field(
                name="Ispezioni",
                value=f"{inspections} ispezioni (€{inspection_salary:,})",
                inline=False
            )
            embed.add_field(
                name="Totale",
                value=f"€{total_salary:,}",
                inline=False
            )

            embed.set_author(
                name=user.display_name,
                icon_url=user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in salary command: {e}", exc_info=True)
            await interaction.response.send_message(
                "Si è verificato un errore durante il calcolo dello stipendio.",
                ephemeral=True
            )

    @ispezione.error
    @stipendio.error
    async def admin_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Non hai i permessi necessari per eseguire questo comando!",
                ephemeral=True
            )
        else:
            logger.error(f"Unexpected error in admin command: {error}")
            await interaction.response.send_message(
                "Si è verificato un errore imprevisto. Riprova più tardi.",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))