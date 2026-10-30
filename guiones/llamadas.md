# Guiones · Tarea 2 · Llamadas de venta (restaurante)

Dominio: **restaurante con delivery**. «Cevichería La Ola» es inventada, igual que los precios, las direcciones y los
teléfonos. **A** es quien vende y **B** es el cliente.

## Carta (precios en soles)

| Producto | Tamaño | Precio |
|---|---|---|
| Ceviche clásico | personal / fuente | 28 / 52 |
| Arroz con mariscos | personal / fuente | 30 / 56 |
| Lomo saltado | personal / fuente | 32 / 60 |
| Ají de gallina | personal | 24 |
| Chicharrón de pescado | personal | 29 |
| Chicha morada | vaso / jarra | 6 / 16 |
| Inca Kola | 1,5 L | 10 |
| Suspiro limeño | unidad | 12 |

**Promociones** (no acumulables):
- 10 soles de descuento en pedidos desde 100 soles.
- Jarra de chicha morada gratis con dos fuentes.
- Suspiro limeño 2×1.

## Trampas en cada llamada

| Clip | Mi rol | El cliente se corrige | Total dicho erróneo | Dirección con números | Total correcto → total dicho |
|---|---|---|---|---|---|
| L01 | B (cliente) | sí (3 lomos → 2) | **sí**: el vendedor resta mal | sí | 122 → 112 |
| L02 | A (vendedora) | sí (ceviche → arroz con mariscos) | no | sí | 114 → 114 |
| L03 | B (cliente) | no | **sí**: aplica dos promociones no acumulables | sí | 102 → 92 |
| L04 | A (vendedora) | sí (quita las Inca Kolas) | **sí**: se olvida la jarra gratis | sí (manzana y lote) | 136 → 152 |
| L05 | B (cliente) | no | no (llamada de control) | sí | 79 → 79 |

---

## L01

**A:** Cevichería La Ola, buenas noches, le habla Kevin. ¿Es para delivery o para recoger?
**B:** Hola, buenas noches, para delivery, por favor.
**A:** Claro. ¿Me dice su pedido?
**B:** Ya, a ver… quiero tres lomos saltados personales.
**A:** Tres lomos saltados personales.
**B:** Y un ceviche clásico, el de fuente.
**A:** Un ceviche clásico fuente. ¿Algo para tomar?
**B:** Una jarra de chicha morada. Ay, espera, espera. Mi hermano me dice que él ya comió. Entonces que sean dos lomos, no tres.
**A:** Ok, corrijo: dos lomos saltados personales, un ceviche clásico fuente y una jarra de chicha morada.
**B:** Eso. ¿Cuánto está el lomo?
**A:** El lomo personal está treinta y dos soles, el ceviche fuente cincuenta y dos y la jarra de chicha dieciséis.
**B:** Ok. ¿Tienen alguna promoción hoy?
**A:** Sí, tenemos un descuento de diez soles en pedidos desde cien soles, así que le aplica.
**B:** Ah, buenísimo.
**A:** ¿A qué dirección se lo enviamos?
**B:** Jirón Huamachuco mil cuatrocientos cincuenta, departamento trescientos dos, en Jesús María. Es un edificio crema, frente a una farmacia.
**A:** Jirón Huamachuco mil cuatrocientos cincuenta, departamento trescientos dos, Jesús María. ¿Un número de contacto?
**B:** Nueve ocho siete, seis cinco cuatro, tres dos uno.
**A:** ¿Y cómo va a pagar?
**B:** Con Yape.
**A:** Perfecto. Entonces su total, con el descuento, sería de ciento doce soles.
**B:** Ciento doce, ok. Te yapeo cuando llegue el motorizado.
**A:** Listo. Su pedido llega en unos cuarenta minutos. Gracias por llamar a La Ola.
**B:** Gracias, hasta luego.

---

## L02

**A:** Cevichería La Ola, buenas tardes, le saluda Milagros. ¿En qué le puedo ayudar?
**B:** Hola, buenas tardes. Quería hacer un pedido para que me lo traigan.
**A:** Claro que sí. Dígame.
**B:** Ya. Primero, un ceviche fuente, para compartir.
**A:** Un ceviche clásico fuente…
**B:** No, no, perdón, mejor cámbialo. Que sea un arroz con mariscos fuente. Ceviche comimos ayer.
**A:** No se preocupe. Entonces, un arroz con mariscos fuente. ¿Qué más?
**B:** Dos chicharrones de pescado, personales.
**A:** Dos chicharrones de pescado personales. ¿Algo de tomar?
**B:** Una Inca Kola de litro y medio. ¿Y cuánto me sale todo eso?
**A:** Le detallo: el arroz con mariscos fuente está cincuenta y seis, cada chicharrón veintinueve y la Inca Kola diez soles. Como su pedido pasa de cien soles, le aplicamos el descuento de diez soles.
**B:** Perfecto.
**A:** ¿La dirección de entrega?
**B:** Avenida Brasil dos mil ochocientos setenta y cinco, en Pueblo Libre. Es una casa con puerta negra; hay que tocar el timbre de arriba.
**A:** Avenida Brasil dos mil ochocientos setenta y cinco, Pueblo Libre, puerta negra. ¿Forma de pago?
**B:** Con tarjeta. ¿El motorizado lleva POS?
**A:** Sí, lleva POS. Entonces le confirmo: un arroz con mariscos fuente, dos chicharrones de pescado personales y una Inca Kola de litro y medio, con el descuento de diez soles. Su total es ciento catorce soles.
**B:** Ciento catorce, perfecto.
**A:** En treinta y cinco a cuarenta minutos lo tiene. Gracias por su preferencia.
**B:** Gracias a ti.

---

## L03

**A:** Buenas noches, Cevichería La Ola, habla Kevin.
**B:** Hola, buenas noches. Quisiera pedir delivery.
**A:** Claro, ¿qué le anoto?
**B:** Tres ajíes de gallina.
**A:** Tres ajíes de gallina, personales.
**B:** Sí. Y de postre, ¿qué tienen?
**A:** Tenemos suspiro limeño, y justo hoy está en dos por uno.
**B:** Ah, ya, entonces dos suspiros.
**A:** Dos suspiros limeños, uno le sale gratis. ¿Para tomar?
**B:** Tres vasos de chicha morada. ¿O me conviene la jarra?
**A:** La jarra está dieciséis y alcanza para unos cuatro vasos; el vaso está seis soles.
**B:** No, somos tres nomás, mejor tres vasos.
**A:** Tres vasos de chicha. ¿Algo más?
**B:** No, eso es todo. ¿Tienen otro descuento? Vi en Instagram algo de diez soles.
**A:** Sí, el de diez soles es para pedidos desde cien, pero las promociones no son acumulables. Le dejo el dos por uno, que le conviene más.
**B:** Ya, perfecto.
**A:** ¿Dirección?
**B:** Calle Los Pinos trescientos cuarenta, en Miraflores, a espaldas del parque Reducto.
**A:** Calle Los Pinos trescientos cuarenta, Miraflores. ¿Cómo paga?
**B:** En efectivo. Voy a pagar con un billete de doscientos, para que el motorizado lleve vuelto.
**A:** Perfecto. Tres ajíes de gallina a veinticuatro, dos suspiros con el dos por uno y tres vasos de chicha morada. Su total es noventa y dos soles.
**B:** Noventa y dos. Ok.
**A:** Le llevamos vuelto de doscientos. Llega en cuarenta y cinco minutos.
**B:** Gracias, chau.

---

## L04

**A:** La Ola, buenas tardes, habla Milagros.
**B:** Hola, buenas tardes, señorita. Para hacer un pedido, por favor; es para una reunión familiar.
**A:** Encantada. ¿Qué le anoto?
**B:** Dos ceviches clásicos, de fuente.
**A:** Dos ceviches clásicos fuente. Le comento que con dos fuentes la jarra de chicha morada le sale gratis.
**B:** ¡Ah, qué bien! Entonces sí, una jarra de chicha. Y aparte, dos Inca Kolas de litro y medio.
**A:** Una jarra de chicha morada y dos Inca Kolas.
**B:** Y un lomo saltado personal, para mi papá, que no come pescado.
**A:** Un lomo saltado personal.
**B:** Oiga, pensándolo bien, quítele las Inca Kolas. Con la chicha alcanza, y mi mamá no quiere gaseosa.
**A:** Listo, le quito las dos Inca Kolas. Entonces: dos ceviches fuente, una jarra de chicha morada y un lomo saltado personal.
**B:** Exacto. ¿Me dice los precios?
**A:** Cada ceviche fuente está cincuenta y dos, la jarra dieciséis y el lomo personal treinta y dos.
**B:** Ok. Es para Carabayllo, ¿llegan hasta allá?
**A:** Sí. ¿Me da la dirección exacta?
**B:** Manzana F, lote doce, urbanización San Antonio, en Carabayllo. Al costado de la losa deportiva.
**A:** Manzana F, lote doce, urbanización San Antonio, Carabayllo. ¿Cómo va a pagar?
**B:** Por Plin.
**A:** Perfecto. Su total es ciento cincuenta y dos soles.
**B:** Ciento cincuenta y dos. Ya, le pagamos cuando llegue.
**A:** Por la distancia, demora más o menos una hora. Gracias por llamar.
**B:** Gracias, señorita.

---

## L05

**A:** Cevichería La Ola, buenas tardes, habla Kevin.
**B:** Hola, Kevin, buenas tardes. Es un pedido para una oficina.
**A:** Claro, dígame.
**B:** Un chicharrón de pescado personal y un ceviche clásico personal.
**A:** Un chicharrón de pescado personal y un ceviche clásico personal. ¿Algo más?
**B:** Un suspiro limeño.
**A:** Le comento que el suspiro está en dos por uno: si pide dos, el segundo es gratis.
**B:** No, gracias, uno nomás, estoy a dieta. Bueno, más o menos.
**A:** Ok, un suspiro. ¿Bebida?
**B:** Una Inca Kola de litro y medio, para compartir con mi compañera.
**A:** Perfecto.
**B:** ¿Y el descuento de diez soles?
**A:** Ese es para pedidos desde cien soles, y el suyo no llega, así que esta vez no hay promoción.
**B:** Ah, ya, no hay problema.
**A:** ¿La dirección?
**B:** Avenida Arequipa cuatro mil ciento veinte, oficina quinientos uno, en Miraflores. Hay que dejarlo en recepción, en el primer piso.
**A:** Avenida Arequipa cuatro mil ciento veinte, oficina quinientos uno, Miraflores; se deja en recepción. ¿Forma de pago?
**B:** Con tarjeta, por favor.
**A:** Le confirmo: chicharrón de pescado personal, veintinueve; ceviche clásico personal, veintiocho; suspiro limeño, doce; e Inca Kola de litro y medio, diez. Su total es setenta y nueve soles.
**B:** Setenta y nueve, perfecto.
**A:** Llega en treinta minutos aproximadamente. Gracias.
**B:** Gracias, Kevin.
