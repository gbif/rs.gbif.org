<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns="http://www.w3.org/1999/xhtml">
    
    <xsl:output method="html"/>
    
    <xsl:template match="*">
        <html>
            <head>
                <title>Name jokes results</title>
            </head>
            <body>
                
                <h1>Name jokes results</h1>
                <xsl:apply-templates select="joke"/>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="joke">
        
        <p>
            <b><xsl:value-of select="question"/>?</b><br/>
            <xsl:value-of select="answer"/>
        </p>
        
    </xsl:template>
    
    
</xsl:stylesheet>