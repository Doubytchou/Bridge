with ada.Text_IO; use ada.Text_IO;
with ada.Command_Line; use ada.Command_Line;

procedure Tester is
   line : string(1..2048);
   last : natural;
   cpt : natural := 0;
begin

   Put_Line(Standard_Error, "Tester launched");
   Put_Line(Standard_Error, "[Tester] Arguments:");
   for I in 1 .. Ada.Command_Line.Argument_Count loop
      Put_Line(Standard_Error,"[Tester] Argument" & Integer'Image(I) & " : " &
                            Ada.Command_Line.Argument (I));
   end loop;
   delay 25.0;

   loop
      Put_Line("request:" & cpt'img);
      Flush;
      Put_Line(Standard_Error, "request:" & cpt'img);
      get_line(line, last);
      if last > 0 then
         Put_Line(Standard_Error, "Response received:" & line(line'first..last));
         flush;
      end if;

      cpt := cpt + 1;
      delay 0.5;
   end loop;


end Tester;
