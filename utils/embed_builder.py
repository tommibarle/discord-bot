import discord
from datetime import datetime

def create_document_embed(author: discord.Member, context: str, index: int = 1, name: str = None) -> discord.Embed:
    """
    Create an embed for the document upload.

    Args:
        author (discord.Member): The user who uploaded the document
        context (str): The context provided for the document
        index (int): The index of the document in the batch
        name (str): The name/identifier for the document group

    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title=f"Documento #{index}" + (f" - {name}" if name else ""),
        description=context,
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )

    embed.set_author(
        name=author.display_name,
        icon_url=author.display_avatar.url
    )

    embed.add_field(
        name="Caricato da",
        value=author.mention,
        inline=True
    )

    if name:
        embed.add_field(
            name="Nome Attività",
            value=name,
            inline=True
        )

    embed.set_footer(
        text="Sistema di Caricamento Documenti"
    )

    return embed