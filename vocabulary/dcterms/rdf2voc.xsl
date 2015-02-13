<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
     xmlns:ext="http://rs.gbif.org/extension/"
     xmlns:voc="http://rs.gbif.org/thesaurus/" 
     xmlns:dcam="http://purl.org/dc/dcam/" 
     xmlns:dc="http://purl.org/dc/terms/" 
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" 
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
     version="1.0"
     >
     
     <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
     <xsl:template match="rdf:RDF">
          <voc:thesaurus 
               xsi:schemaLocation="http://rs.gbif.org/thesaurus/  http://rs.gbif.org/schema/thesaurus.xsd"
               dc:URI="" 
               dc:description="" 
               dc:title="">
               <xsl:apply-templates select="//rdf:Description">
                    <!-- <xsl:sort select="@group"/> -->
               </xsl:apply-templates>
          </voc:thesaurus>
     </xsl:template>
     
     <xsl:template match="rdf:Description">
          <voc:concept dc:identifier="preservedspecimen" dc:URI="http://rs.tdwg.org/dwc/dwctype/PreservedSpecimen"  dc:issued="2008-12-17T04:31:07+00:00">
               <xsl:attribute name="dc:identifier">
                    <xsl:value-of select="rdfs:label"/>
               </xsl:attribute>
               <xsl:attribute name="dc:URI">
                    <xsl:value-of select="@rdf:about"/>
               </xsl:attribute>
               <voc:preferred>
                    <voc:term dc:modified="2008-12-18T04:54:28+00:00" dc:source="" dc:title="Preserved Specimen" xml:lang="en">
                         <xsl:attribute name="dc:title">
                              <xsl:value-of select="rdfs:label"/>
                         </xsl:attribute>
                         <xsl:attribute name="xml:lang">en</xsl:attribute>
                         <xsl:attribute name="dc:source">Dublin Core RDF</xsl:attribute>
                    </voc:term>
               </voc:preferred>
               <voc:alternative>
               </voc:alternative>
          </voc:concept>
     </xsl:template>
     
</xsl:stylesheet>
