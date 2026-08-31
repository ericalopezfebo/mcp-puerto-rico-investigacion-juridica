"""Extended discovery-only authority directory from 2025 legal course indexes.

This module adds Hipotecario/Registral, Familia, Derechos Reales and Sucesiones
as context for discovery. It is never legal authority by itself. Directory hits
must still be verified against primary sources before citation or reliance.
"""
from __future__ import annotations

import re
from typing import Any

import mixed_server
import search_tuning
import server as jurisprudencia

# Source-derived case/citation directory. Third field: 1 = OCR/name/citation control required.
# A few malformed OCR rows are intentionally retained in RAW but filtered at load time.
RAW = r'''@@derecho hipotecario y registral
Consejo de Titulares v. MGIC Financial Com., 12	128 DPR 538	0
Nombre no legible en OCR	2019 TSPR 43	1
de proteger terceros adquirentes que confiaran i realizar su adquisicion, Roda Development v. fe publica registra es la bas propésito de la Ley Hipotecaria es	123 DPR 547	1
Nombre no legible en OCR	137 DPR 70	1
Nombre no legible en OCR	181 DPR 625	1
que exisia una concordancia entre ja realidad juridica, San Gerdnimo Caribe Project v. Bajo este princi inscritos se ajuste & del Registro y Jos asientos Registadora	2013 TSPR 198	1
Nombre no legible en OCR	2015 TSPR 197	1
Vazquer v. ARPE	128 DPR 513	0
Park Tower v. Reaistradora	2015 TSPR 157	0
Haedo Casto v. Reidén Morales	2019 TSPR 176	0
Ex Parte Torres Barer	2025 TSPR 5	0
Pagan Heréndez Fr Panén Heméndez v. Registradore	177 DPR 622	0
Nombre no legible en OCR	2023 TSPR 91	1
TSPR 8. Suficiente para denegar 1 supremo explca én DLJ Mortgage Capital v. Garela Remos	2024 TSPR 66	1
Nombre no legible en OCR	2025 TSPR 8	1
Nombre no legible en OCR	430 DPR 817	1
propiedad. ‘Segregaciones y testamentos Pino v. Negrén	138 DPR 373	0
In re Vargas Velazquez	2015 TSPR 120	0
fotalidad de su derecho hereditario a favor de un tercero. Miranda Meléndez v. Registrador	2015 TSPR 132	0
Lorenzo Hemandez v, Morales Nieves	2017 TSPR 8	1
In re Salveti Maldonado, 2028 TSPR 91. de Surilo	2023 TSPR 124	0
In re Salveti Maldonado	2028 TSPR 91	0
ola autorizacion te Atculo 132 codifica la jursprudencia estableciGa ef Vega Montoya v. Zayas, 179 oR 80 (2010) y Narvaez ie Registrador	156 DPR 1	0
Pino v. Nears	133 DPR 373	0
Distibuidores Unidos de Gas v. Marchand Ce astro	2013 TSPR 43	0
Solo Sold v. Registradora	2013 TSPR 115	0
Speers Unidos de Gas de Puerto Rico, Inc. v. Sucesion	2016 TSPR 171	0
Parras Silvestry v. Registradora	2020 TSPR 5	0
Santiago v. ELA	163 DPR 149	0
Rigores, Ine v. Regisvador	165 DPR 710	0
Pérez Rivers v. Redisradora	2019 TSPR 122	0
Nombre no legible en OCR	2021 TSPR 00	1
Western Federal v. Reaistrador, aclaraciones de importancia	499 DPR 328	0
Cin v. Borés	144 DPR 91	0
In te Storgantes deben incluir su est Jes	161 DPR 219	1
deciare los respecives derechos de las Iiites, Banco Popular de Puerto Rico v. Zorrila Posada	2024 TSPR 62	0
In re Godinez Morales	461 DPR 219	0
Nombre no legible en OCR	117 DPR 662	1
impidan la inscripcién del documento. E]. Falta de tracto sucesivo. BL Investment v. Quifones	173 DPR 833	0
vatoracion lez v. Registradora	177 DPR 522	0
San. Gronks Caribe Project v. Registracora	2013 TSPR 138	0
Nombre no legible en OCR	126 DPR 209	1
Rios v. Cacho	130 DPR 817	0
Pagan HemAndez v. Registradora	177 DPR 822	0
Pedragén Ferret v. Purcell Sole	2016 TSPR 243	0
ORIM v. Regisiadora	2079 TSPR 137	0
Nombre no legible en OCR	2009 TSPR 65	1
facultad confers por suvtespecive ey nabiiadors,” Ss nome Nos aclara United Surety v. Registradora	2015 TSPR 4	0
alist ey istradora	2013 TSPR 122	1
Nombre no legible en OCR	2015 TSPR 137	1
registro.) Fist Bank Puerto Rico v. Registradora	2021 TSPR 135	0
Acosta Lebron v. Reaistrador	159 DPR 626	0
adicidn a la finca remanente. Art. 147. Parras Silvestry v. Reaistradora	2020 TSPR 6	1
pueden sarmoan privativas, porque no son del mismo dueio. Gaztambide Vda, Arriaga v. Sucesién Ortiz	70 DPR 412	1
Atocha v. Registrador	123 DPR 871	0
Pueblo International v. Reaistrador	101 DPR 701	0
Banco Popular v. Registrar	172 DPR 448	0
Seon Soto Hemandez v. Registradora	175 DPR 975	0
Art. 35 Santander v. Rosatio	126 DPR 591	1
Aves ¥ va, ademas donstruclon	108 DPR 225	1
Infante v. Masso	165 DPR 474	0
Rosario v. Reaistrador	115 DPR 491	0
obtenga una orden del stradora, 183 DPR 610 (2011) y Quifiones Reyes v. ed Bechara Fane oak } jistrador	175 DPR 86	0
Bechara Faqundo v. Reaistradora	183 DPR 610	0
Quifiones Reyes v- Reaistrador	175 DPR 861	1
Nombre no legible en OCR	162 DPR 602	1
In re Charbonier Laureano	156 DPR 575	0
in re Velez Béez	176 DPR 201	0
Nombre no legible en OCR	181 DPR 663	1
ese cao ae pagar aranceles por nvecreoe Sir Sic hpoteca, 1 que sea mayo” Cooperalva de Aho v. Conse de Tiulares ond. Beach Village	2016 TSPR 79	1
DLJ Mortgage v. Garcia	2021 TSPR 66	0
Delaado Pol v. Pietri Vélez	2022 TSPR 2	0
o sea, que tiene qu inscripcion que exista, Matos Rivera v. Soler Ortiz	2024 TSPR 80	1
Matos Rivera v, Soler Oriz	2024 TSPR 60	1
Nombre no legible en OCR	115 DPR 277	1
Nombre no legible en OCR	18 DPR 123	1
adquirente del bien hipotecado, pero no al ue esta dspOstion os. Perdomo v. Suc. Cinkén	114 DPR 126	0
estpulare qu lapoteca ifereses por un plazo superior a 5 anos. Campos v. Com; 3520 Indusiial	153 DPR 197	0
atrasados por un término mayor a cinco (6) Siios. Nos dice Campos v. Compajita de Fomento Industral	183 DPR 137	0
Nombre no legible en OCR	163 DPR 137	1
ellos de eilcmentos neg Se ee Constr ave vO Ae cambios efectuados. v. Red	2024 TSPR 135	0
Nombre no legible en OCR	169 DPR 10	1
lleva consigo fa hulldad de la subasta. eso de Lincoln Savings Bank v. Figueroa	124 DPR 388	0
Ant. 104 ipo minimo, subasta seré asriquez Morales v. Redstador	142 DPR 247	0
Nombre no legible en OCR	181 DPR 669	1
Pedragén Ferrer v. Purcell Soler	2016 TSPR 249	1
Nombre no legible en OCR	170 DPR 135	1
Nombre no legible en OCR	106 DPR 361	1
@@derecho de familia
Soto Cabral v. ELA	138 DPR 298	0
no exista un derecho fundamental al aborto bajo la constitucién federal. Pueblo v. Duarte Mendoza	109 DPR 596	0
Pueblo v. Garcia Colén	182 DPR 129	0
Rivera Schatz v. ELA	2014 TSPR 122	0
Cintron Roman v. Jiménez Echevarria	2023 TSPR 59	0
Santos Iglesias v. Lugo Oliveras	2023 TSPR 83	0
Ex Parte Delgado Hemandez	165 DPR 170	0
Gonzalez Hernandez v. Gonzalez Hemandez	181 DPR 746	0
Carrillo Vazquez v. Rodriquez Cintrén	2019 TSPR 110	0
Caquias v. Asociacién de Reside ites	134 DPR 181	0
Sociedad de Gananciales Scotiabank de Puerto Ric v. TCG	2017 TSPR 88	0
forma sustancial su capacidad econémica. ‘Sola Gutiérrez v. Bengoa	182 DPR 675	0
Vilanova v. Vilanova	2012 TSPR 53	0
&pocas de descanso. Los casos de Rodriguez Rivera v. De Leon Otafio	2014 TSPR 123	1
In re Yero Vicente	2020 TSPR 100	0
le pone “integrante de la Sucesi6n", no le van a desestimar. Vega v. Garcia	61 DPR 99	0
Obergefell v. Hodges	135 S. Ct. 2584	0
contempla algiin funcionario que se niegue a inscribir un matrimonio homosexual. Pavan v. Smith	137 S. Ct. 2015	1
dolo nunca anula el matrimonio, por maquinacion insidiosa que sea. Rosado v. Rivera	81 DPR 158	1
contexto de un matrimonio anulable se llama Diaz v. M.M.M.	110 DPR 187	0
Lopez v. Valdespino	6 DPR 172	0
un ser humano distinto al que creias que te estabas, casando. Rosado v. Rivera	81 DPR 156	1
Meléndez Soberal v. Garcia Marrero	158 DPR 77	0
Pueblo v. Jordan	118 DPR 592	0
In re Gonzalez Porrata-Doria	158 DPR 150	0
Alvarado Colén v. Alemafiy	157 DPR 672	0
Mufiiz Noriega v. Mufioz	177 DPR 967	0
Torres Vélez v. Soto	2013 TSPR 144	0
Diaz v. Alcala	140 DPR 959	0
Lépez v. Gonzalez	163 DPR 275	0
Meléndez v. Maldonado	175 DPR 1007	0
Pagan Hernandez v. Registradora	177 DPR 522	0
esos fines, por justa causa, sin el consentimiento del otro cényuge. Padré v. Espada	111 DPR 56	0
Betancourt Gonzalez v. Pastrana Santiago	2018 TSPR 68	0
Rosellé Puig v. Rodriguez Cruz	183 DPR 81	0
Correa Marquez v. Carmen J i Rodi uez	2017 TSPR 98	0
Montalvan v. Rodriguez	161 DPR 411	0
BL Investments v. Rivera	181 DPR 5	0
Diaz Rodriquez v. Garcia Ner	2022 TSPR 12	0
Ab Intestato Saldafia	126 DPR 640	1
Guadalupe v. Gonzélez	172 DPR 676	0
Maldonado v. Cruz Davila	161 DPR 1	0
Caraballlo v. Acosta	104 DPR 474	0
incapacitado lo contrae sujeto al régimen de sociedad de gananciales. Gil v. Marini	167 DPR 553	0
Gonzalez Rivera v. Robles Laracuente	2019 TSPR 225	0
Rivera v. Algarin	159 DPR 482	0
Torres Gonzalez v. Zaragoza Meléndez	2023 TSPR 46	0
Vivoni Farage v. Ortiz Carro	179 DPR 990	0
Candelario v. Mufiz	171 DPR 530	0
Crespo v. Santiago	176 DPR 408	0
De Leon v. Hospital Universitario	174 DPR 393	0
Martinez v. McDougal	133 DPR 228	0
decir, que una vez transcurre, ya no se puede hacer nada. Bonilla v. Davila	185 DPR 667	1
Pérez Rodriguez v. Lopez Rodriguez	2022 TSPR 95	0
un testamento, ocurriria la pretericién. Robles v. Izquierdo	134 DPR 426	0
L6pez Rivera v. ELA	165 DPR 280	0
Beniquez Méndez v. Vargas Sein	184 DPR 210	0
Jusino Gor lez v. Norat Santiago	2023 TSPR 47	0
Rios v. Vidal	134 DPR 3	0
Alvareztorre v. Sorani	175 DPR 398	0
Caez v. U.S. Casualty	80 DPR 754	0
Toro Sotomayor v. Colén	176 DPR 528	0
no pudo evitar el dafio, no procedera la demanda contra él. Lopez v. Porrata Doria	156 DPR 503	0
Rosario v. Gonzalez	157 DPR 636	0
Garcia v. Ramirez	155 DPR 91	0
Ex Parte Rivera Rios	173 DPR 678	0
este articulo no son aplicables cuando el acto u omisin a v. constituye delito o cuando no haya unidad familiar que proteger. Ver D: Meléndez	2013 TSPR 12	1
Crespo v. Cintrén	159 DPR 290	0
Rexach v. Ramirez Vélez	162 DPR 130	0
emancipado queda liberado de la patria potestad o de la tutela. Miranda v. Municipio de Barceloneta	122 DPR 619	0
Martinez v. Ramirez Tid	133 DPR 219, 226	0
Sucesién De Jestis v, Sucesién Castro	62 DPR 580	1
Sucesién De Jestis v, Sucesién Castro, 62 DPR 580 (1943) y Alvarez v. Aponte	83 DPR 617	0
Nombre no legible en OCR	110 DPR 877	1
Registro Demografico. Martinez v. Ramirez Tid	133 DPR 219, 225	0
Pifiero v. Gordillo	122 DPR 246	0
Pifiero v. Gordillo, 122 DPR 246 (1988) y Martinez de Andino v. Martinez de Andino	184 DPR 3	0
Pifiero v. Gordillo, 122 DPR 246 (1988) y Martinez de Andino v. Martinez de Andino	184 DPR379	0
Rodriquez v. ayas	133 DPR 406	0
Santiago Texidor v. Maisonet	187 DPR 550	0
De Leon Ramos v. Navarro Acevedo	2016 TSPR 60	0
Fuentes v. Colén Molina	2019 TSPR 55	0
Ortiz v. Vazquez	119 DPR 547	0
Morales v. ime	166 DPR 282	0
Key v. Oyola	116 DPR 261	0
Rodriquez v. Santiago	133 DPR 785	0
Rivera Medina v. Villafafie	186 DPR 289	1
Umpierre Matos v. Juelle Abello	2019 TSPR 160	0
por Z, el tribunal cada vez que las circunstancias cambien. Otero Vélez v. Schroder Mi	2018 TSPR 56	1
evidente temeridad y obstinacién ante las ordenes reiteradas de cumplimiento."Ver Montes Diaz v. Montes James	2024 TSPR 27	0
Suria v. Femandez	101 DPR 316	0
Suria v. Femandez, 101 DPR 316 (1973) y Brea v. Pardo	113 DPR 217	0
es el bienestar del alimentista y no penalizar al alimentante. Rodriquez Avilés v. Rodriguez Beruff	117 DPR 616	0
@@derechos reales
Betancourt Gonzalez v. Pastrana Santiago	2018 TSPR 68	0
Lozada Ocasio v. Registrador	99 DPR 435, 442	0
Hato Rey Electroplating v. Rodriquez	114 DPR 286	0
cosa o suscribiendo la escritura o documento privado que la transfiere. Trabal v. Ruiz	125 DPR 340	1
Asociacién v. Cardona	144 DPR 1	0
de uso piiblico. Watchtower Bible and Tract Society of New York, Inc. v. Municipio de Dorado	2014 TSPR 138	0
privada y readquieren su primitiva condicién tan pronto cesan dichos fines. Figueroa v. Municipio	98 DPR 534	0
éso les va a indicar si es un inmueble por incorporaci6n. Romaguera v. Tribunal	61 DPR 114	0
Ramirez v. Soto	168 DPR 142	0
Arce v. Diaz	77 DPR 624	0
Consejo de Titulares v. Galerias Poncefias, Inc.	145 DPR 315	0
Nombre no legible en OCR	48 DPR 884, 889	1
finca y los restantes datos necesarios para su deslinde y amojonamiento. Zalduondo v. Méndez	74 DPR 637	0
que invadan su terreno, las puede cortar el vecino sin permiso. Vélez v. Latimer	125 DPR 109	1
Marin v. Montijo	109 DPR 268	0
E.L.A. v. Tribunal	94 DPR 157	0
CRUV v. Roman	100 DPR 318	0
lo plantado o lo sembrado sin derecho a indemnizacion. Autoridad de Tierras v. Padin	104 DPR 426	0
Laboy Roque v. Pérez	181 DPR 718	1
Mc Gonzalez v. Alvarez Gerena	2019 TSPR 191	0
iguales, a menos que se pruebe lo contrario. Art. 837. Gonzalez Rivera v. Robles Laracuente	2019 TSPR 225	1
Matos Rivera v. Soler Ortiz	2024 TSPR 50	0
Diaz v. Aguayo	162 DPR 801	0
una sentencia titulada Meléndez v. Maldonado	175 DPR 1007	0
Cruz Roche v. De Jess Colén	182 DPR 313	0
Asociacion v. Arsuaga	160 DPR 289	0
pueden modificar el destino y la naturaleza de ésta. De la Fuente v. Roig	82 DPR 514	0
Gonzalez v. Sucesion Cruz	163 DPR 449	0
de tiguroso dominio que requiere el consentimiento undnime de los herederos. Gual v. Pérez	72 DPR 609, 615-16	1
Residentes Parkville Sur v. Diaz	159 DPR 374	0
Asoc. de Vecinos de Villa Caparra v. Asoc. de Fomento Educativo	173 DPR 304	0
voluntaria persigue la cosa, no importa los duefios que tenga. Pérez Rivera v. ‘egistradora	2013 TSPR 122	1
Park Tower v. Registradora	2015 TSPR 157	0
Ramirez Kurtz v. EA Ramos	2024 TSPR 97	0
Dorado del Mar Estates v. Carlos Weber	2019 TSPR 137	0
Asoc. Pro Bienestar Vecinos v. Santander	157 DPR 521	0
Asociacién de Propietarios de Playa Hucares v. Rodriguez	167 DPR 255	0
Femandez Martinez v. RAD-MAN San Juan, LLC	2021 TSPR 149	0
Davila v. Cérdova	77 DPR 136, 141	0
Sanchez v. Registrador	106 DPR 361	0
Sanchez Gonzdlez v. Registrador	106 DPR 361, 375	0
concepto de duefio. lez v. Medina	99 DPR 113	0
Bravman v. Consejo de Titulares	183 DPR 827, 879	0
Miranda Cruz v. Ritch	176 DPR 951	0
0 abonar el aumento de valor que por ellos haya adquirido la cosa. Jiménez v. Reyes	146 DPR 257	1
Mercado Vélez v. Mercado White	2024 TSPR 85	0
° () los ejecutados con violencia. Catalan v. Garcia	104 DPR 380	0
Bravman v. Consejo de Titulares	2011 TSPR 189	0
de mala fe. Administracién de Terrenos v. Rivera Morales	2012 TSPR 157	0
° () los ejecutados con violencia. Catalan v. Garcia, 104 DPR 380 (1975) y Amézquita v. Hernandez	518 F.2d 8	0
Alvarez v. Gonzalez Lamela	134 DPR 374, 384	0
Alvarez v. Gonzalez Lamela	134 DPR 374, 384-85	0
duefia de ellla, y por tanto podia transmitir su dominio. Sucesién Maldonado v. Sucesién Maldonado	166 DPR 154	0
Nissen v. Genthaller	172 DPR 503, 513	0
Heméndez v. Caraballo	74 DPR 29	0
In re Marquez Colén	2017 TSPR 129	0
segunda planta para obstruir la vista al duefio del predio dominante. Delgado v. Girau	115 DPR 61	0
Sociedad de Gananciales v. Municipio de Aquada	144 DPR 114	1
suficientes para la utilizacion normal de la finca dominante. Sociedad de Gananciales v. Secretario de Justicia	137 DPR 70	0
particién, no hay que indemnizar. Rosa v. Medina	89 DPR 456	1
Lozada v. Registrador	99 DPR 435	0
por una disminucién del precio proporcional a la gravedad del perjuicio. Colén v. Registrador	114 DPR 850	0
necesidad de hacerlas. Art. 901. &. Dafios causados por un huracan. Boerman v. Herederos de Boerman	52 DPR 611	1
Rodriguez Diaz v. ELA	174 DPR 194	0
P.D.C.M. Associates v. Najul Bez	174 DPR 216	0
Nombre no legible en OCR	132 DPR 39	1
Rodriguez v. Rivera	71 DPR 290	0
Rodriguez v. Rivera, 71 DPR 290 (1950) y Sucesién Rosario Andino v. Rosario Andino	85 DPR 135	0
obra. Moreno v. Sumley	2012 TSPR 179	0
@@sucesiones
Nombre no legible en OCR	128 DPR 565	1
Nombre no legible en OCR	2016 TSPR 236	1
persona responde por evicción y por los defectos ocultos del bien. Rivera v. E.LA.	111 DPR 109	0
Banco Popular v. Registrador	172 DPR 448	0
Velázquez v. Velázquez	82 DPR 619	0
Blassino Alvarado v. Reyes Blassino	2024 TSPR 93	0
casos de La Costa v. Costa	112 DPR 9	0
casos de La Costa v. La Costa, 112 DPR 9 (1982) y Senior Las Marías Corp. v. Registrador	113 DPR 675	0
Reyes v. Jusino	116 DPR 275	0
documento puede ser procesado éticamente, por violar la fe pública notarial. Reyes v. Jusino	116 DPR 291	0
Rivera v. Monge	117 DPR 464	0
beneficiar con el negocio, permaneciendo oculta la que verdaderamente lo realiza. Martínez v. Colón	125 DPR 15	1
momento de la muerte del causante. Art. 1547. Arrieta v. Chinea Vda. de Arrieta	139 DPR 525	1
Sucesión Toro Morales v. Sucesión Toro Cruz	161 DPR 391	0
cuanto a esa parte. Fernández Franco v. Castro Cardoso	119 DPR 154, 161	0
una parte alícuota, designada a título particular. Torres Martínez v. Torres Ghigliotty	175 DPR 83	0
Lorenzo Hernández v. Morales Nieves	2017 TSPR 8	0
Ruiz Mattei v. Commercial Equipment Finance, Inc.	2024 TSPR 68	0
Vda. de Delgado v. Boston Insurance	101 DPR 598	0
sufrieron una interrupción efectiva de ingreso proveniente del patrimonio del causante. Rivera v. Fondo del Seguro	113 DPR 334	0
Blás Toledo v. Hospita! de la Guadalupe	146 DPR 626	0
Vázquez Pagán v. Fondo del Seguro	2011 TSPR 156	0
Santiago Montañez v. Fresenius Medical Care	2016 TSPR 76	0
al asegurado, y si éste muere, a sus herederos. Vda. de Méndez v. Superior	102 DPR 553, 557	0
Pilot Life Insurance v. Crespo	136 DPR 624	0
Vélez Rivera v. Bristol- Myers Squibb	158 DPR 130	0
Torres Torres v. Torres Serrano	179 DPR 481	0
In re Rodríguez Cora	2015 TSPR 99	0
Island Holdings, Ltd. v. Sucesión Flavio Enrique Hernández	2019 TSPR 42	1
mentales del causante se heredan por los hijos y descendientes. Blás Toledo v. Hospital de la Guadalupe	146 DPR 267	0
Transamerica v. Rodríguez	170 DPR 804	0
Sucesión Caragol v. Registrador	174 DPR 74	0
In re De la Texera Bames	177 DPR 468	0
In re Clavell	131 DPR 500	0
In re Martinez Almodóvar	2011 TSPR 23	0
In re Berríos Pérez	172 DPR 334	0
In re Mesonero Hernández	173 DPR 632	0
Deliz Muñoz v. Igartúa Muñoz	158 DPR 403	0
García Colón v. Sucesión	178 DPR 527	0
In Re Medina	113 DPR 177	0
In re Irlanda Pérez	162 DPR 358	0
In re Rosado Nieves	2013 TSPR 92	0
como si no supiera firmar y se cumplirá con los requisitos. Canales v. Aldea	69 DPR 969	0
In re Flores Castro	170 DPR 802	0
Rabel v. Registradora	2008 TSPR 112	0
García Colón v. Sucesión	2010 TSPR 36	0
Cabrer v. Registrador	113 DPR 424	0
In re Nazario Díaz I	174 DPR 99	0
Blanch v. Registrador	59 DPR 730	0
Nombre no legible en OCR	126 DPR 84	1
Licari v. Dorna	148 DPR 453	0
bienes de la herencia corresponde a los herederos forzosos (legitimarios). Fernández v. Castro	119 DPR 154	0
Bonilla v. Dávila	185 DPR 667	0
reválida de derecho más de 3 veces. Jarra Corporation v. Axxis Corp.	155 DPR 764	0
Dávila v. Agrait	116 DPR 549	0
con la obligación de conservar y de entregar a otro heredero. Díaz v. Luciano	85 DPR 834	0
Blanco v. Sucn. Blanco	106 DPR 471	0
Nombre no legible en OCR	126 DPR 640	1
Moreda v. Rosselli	141 DPR 674	0
Rivera v. Sanoguet	164 DPR 756	0
y (e) — las establecidas por el testador. Alejandro v. Superior	100 DPR 600	0
Freire Ruiz de Val v. Morales Roman	2024 TSPR 129	0
Pino v. Negrón	133 DPR 373	0
Flecha v. Lebrón	166 DPR 330	0
Tous Redríguez v. Sucesión Tous Oliver	2023 TSPR 106	0
Una ilustración Valladares v. Rivera	89 DPR 254	0
Vilanova v. Vilanova	2012 TSPR 53	0
Gierbolini v. Registrador	151 DPR 315	0
Carrillo Vázquez v. Rodríguez Cintrón	2019 TSPR 110	0
este caso existente la personalidad del difunto.” Figueroa v. Registrador	18 DPR 260	0
Schluter v. Sucesión Díaz	46 DPR 636	0
González Campos v. González Mezerene	139 DPR 228, 247-248	0
Escalona v. Sucesión Castro	17 DPR 774, 784	0
simultáneamente, puede aceptarla por un concepto y repudiarla por otro. Torres Ginés v. ELA	118 DPR 436	0
Vega Montoya v. Zayas, 179 DPR 80 (2010) y Kogan v. Registrador	125 DPR 636	0
Vega Montoya v. Zayas	179 DPR 80	0
Miranda Meléndez v. Registrador	2015 TSPR 132	0
Sepúlveda v. Registradora	125 DPR 401	0
donación. Rodriguez Pérez v. Sucn. Rodríguez	126 DPR 284	0
In re Curas Ortiz	2008 TSPR 147	0'''

_CITATION_RE = re.compile(r"(?i)(?:\b(?:19|20)\d{2}\s*TSPR\s*\d{1,4}\b|\b\d{1,3}\s+DPR\s*\d+|\b\d{1,3}\s+S\.\s*Ct\.\s*\d+|\b\d+\s+F\.2d\s+\d+)")


def _norm(text: str) -> str:
    return jurisprudencia.normalize_text(text or "")


def _load() -> tuple[dict[str, Any], ...]:
    area = ""
    out: list[dict[str, Any]] = []
    for raw_line in RAW.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("@@"):
            area = line[2:].strip()
            continue
        parts = line.rsplit("\t", 2)
        if len(parts) != 3:
            continue
        case, citation, ocr = (p.strip() for p in parts)
        if not _CITATION_RE.search(citation):
            continue
        out.append({"area": area, "case": case, "citation": citation, "ocr_check": ocr == "1"})
    return tuple(out)


AUTHORITIES = _load()

# Area-level doctrine vocabulary is discovery context only. It does not assert a holding.
AREA_TERMS: dict[str, tuple[str, ...]] = {
    "derecho hipotecario y registral": (
        "registro de la propiedad", "calificacion registral", "tracto sucesivo", "fe publica registral",
        "hipoteca", "anotacion preventiva", "tercero registral", "segregacion", "recurso gubernativo",
        "pagare hipotecario", "ejecucion de hipoteca", "subasta",
    ),
    "derecho de familia": (
        "matrimonio", "divorcio", "sociedad de gananciales", "comunidad postganancial", "alimentos",
        "custodia", "patria potestad", "filiacion", "adopcion", "emancipacion", "concubinato",
        "capitulaciones matrimoniales", "paternidad", "inmunidad familiar",
    ),
    "derechos reales": (
        "derecho real", "posesion", "usucapion", "servidumbre", "restriccion voluntaria", "comunidad de bienes",
        "accesion", "usufructo", "derecho de superficie", "retracto", "opcion de compra", "deslinde",
    ),
    "sucesiones": (
        "sucesion", "herencia", "testamento", "legitima", "pretericion", "desheredacion", "legado",
        "albacea", "contador partidor", "particion", "colacion", "comunidad hereditaria", "herencia yacente",
        "aceptacion de herencia", "repudiacion de herencia", "derecho a acrecer", "donacion",
    ),
}

# Legislative/source hints supported by the supplied indexes. They are pointers for research,
# not verified statements of current law. The MCP's vigencia/primary-source tools remain controlling.
LEGAL_SOURCE_HINTS = (
    {"source": "Codigo Civil de Puerto Rico de 2020", "areas": ("derecho de familia", "derechos reales", "sucesiones"), "status": "discovery_only_verify_current_text"},
    {"source": "Ley Hipotecaria y del Registro de la Propiedad de Puerto Rico", "areas": ("derecho hipotecario y registral",), "status": "discovery_only_verify_current_text"},
    {"source": "Ley de Transacciones Comerciales", "areas": ("derecho hipotecario y registral",), "status": "discovery_only_verify_current_text"},
    {"source": "Ley de Sustento de Menores / ASUME", "areas": ("derecho de familia",), "status": "discovery_only_verify_current_text"},
    {"source": "Reglas de Procedimiento Civil", "areas": ("derecho hipotecario y registral", "derecho de familia", "sucesiones"), "status": "discovery_only_verify_current_text"},
)


def _areas_for_query(query: str) -> set[str]:
    q = _norm(query)
    matched: set[str] = set()
    for area, terms in AREA_TERMS.items():
        if _norm(area) in q or any(_norm(term) in q for term in terms):
            matched.add(area)
    return matched


def directory_matches(query: str, maximo: int = 30) -> list[tuple[float, dict[str, Any]]]:
    q = _norm(query)
    qtokens = {t for t in q.split() if len(t) >= 4}
    target_areas = _areas_for_query(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in AUTHORITIES:
        case = _norm(str(row["case"]))
        citation = _norm(str(row["citation"]))
        area = str(row["area"])
        blob = f"{case} {citation} {_norm(area)}"
        score = 0.0
        if q and len(q) >= 5 and q in blob:
            score += 14.0
        score += min(10.0, sum(1 for token in qtokens if token in blob) * 1.5)
        if area in target_areas:
            score += 4.0
        if case and (case in q or q in case):
            score += 10.0
        if citation and citation in q:
            score += 12.0
        if row["ocr_check"]:
            score *= 0.72
        if score > 0:
            scored.append((round(score, 2), row))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1]["case"])))
    return scored[:max(1, min(int(maximo), 100))]


_original_expanded_query_terms = search_tuning.expanded_query_terms


def expanded_query_terms_with_extended_directory(query: str) -> list[tuple[str, float]]:
    weighted: dict[str, float] = dict(_original_expanded_query_terms(query))
    for area in _areas_for_query(query):
        weighted[_norm(area)] = max(weighted.get(_norm(area), 0.0), 0.50)
        for term in AREA_TERMS[area]:
            nt = _norm(term)
            if nt in _norm(query):
                weighted[nt] = max(weighted.get(nt, 0.0), 0.82)
    for _score, row in directory_matches(query, 16):
        case = _norm(str(row["case"]))
        citation = _norm(str(row["citation"]))
        if case and "nombre no legible" not in case:
            weighted[case] = max(weighted.get(case, 0.0), 0.45 if row["ocr_check"] else 0.68)
        if citation:
            weighted[citation] = max(weighted.get(citation, 0.0), 0.58)
    return sorted(weighted.items(), key=lambda item: (-item[1], item[0]))


search_tuning.expanded_query_terms = expanded_query_terms_with_extended_directory


@mixed_server.mcp.tool()
async def buscar_directorio_autoridades(consulta: str, maximo: int = 20) -> dict[str, Any]:
    """Busca casos semilla del directorio auxiliar. No verifica ni sustituye la búsqueda jurídica."""
    matches = directory_matches(consulta, maximo)
    return {
        "consulta": consulta,
        "resultados": [
            {
                "materia": row["area"],
                "caso": row["case"],
                "cita": row["citation"],
                "requiere_cotejo_ocr": row["ocr_check"],
                "nivel": "directorio_descubrimiento_no_verificado",
                "ranking_directorio": score,
            }
            for score, row in matches
        ],
        "total_directorio_extendido": len(AUTHORITIES),
        "fuentes_legales_contextuales": [x["source"] for x in LEGAL_SOURCE_HINTS],
        "regla_verificacion": "El directorio solo aporta contexto y semillas. Debe continuarse la busqueda y verificarse nombre, cita, vigencia, tratamiento, proposicion y pinpoint en fuente oficial.",
    }


@mixed_server.mcp.tool()
async def estado_directorio_autoridades() -> dict[str, Any]:
    by_area: dict[str, int] = {}
    ocr = 0
    for row in AUTHORITIES:
        by_area[row["area"]] = by_area.get(row["area"], 0) + 1
        ocr += int(row["ocr_check"])
    return {
        "registros_validos": len(AUTHORITIES),
        "por_materia": by_area,
        "entradas_con_control_ocr": ocr,
        "fuentes_legales_contextuales": list(LEGAL_SOURCE_HINTS),
        "uso": "descubrimiento_y_contexto_no_autoridad",
        "busqueda_y_verificacion_siguen_siendo_obligatorias": True,
    }
