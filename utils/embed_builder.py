import discord
from datetime import datetime

def create_document_embed(author: discord.Member, context: str) -> discord.Embed:
    """
    Create an embed for the document upload.
    
    Args:
        author (discord.Member): The user who uploaded the document
        context (str): The context provided for the document
        
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title="Document Upload",
        description=context,
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_author(
        name=author.display_name,
        icon_url=author.display_avatar.url
    )
    
    embed.add_field(
        name="Uploaded by",
        value=author.mention,
        inline=True
    )
    
    embed.set_footer(
        text="Document Upload System"
    )
    
    return embed
