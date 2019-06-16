        @   /0000
INIT    IO  /1        ; Get Data from device
        MM  IADDR     ; Save first byte of initial address
        IO  /1
        MM  IADDR+1   ; Save second byte of initial address
        IO  /1
        MM  SIZE      ; Save size

LOOP    IO  /1        ; Read byte from file
        CN  /2        ; Activate Indirect Mode
        MM  IADDR     ; Indirect move to current address

        LD  IADDR+1   ; Get current address
        +   ONE       ; Sum 1
        MM  IADDR+1   ; Put it back

        LD  SIZE      ; Get size
        -   ONE      ; Subtract 1
        MM  SIZE      ; Put it back

        JZ  END       ; Finish if size = 0
        JP  LOOP

END     OS  /F        ; End Program

IADDR   K   0
        K   0
SIZE    K   0
ONE     K   1
        # INIT