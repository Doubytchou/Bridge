with ada.Text_IO; use ada.Text_IO;
with ada.Strings.Fixed; use Ada.Strings.Fixed;
with ada.Command_Line; use ada.Command_Line;
procedure Server is
   line : string(1..2048);
   last : Natural;
   ind : NAtural;
begin
   Put_Line(Standard_Error, "[Server] Launched");
   Put_Line(Standard_Error, "[Server] Arguments:");
   for I in 1 .. Ada.Command_Line.Argument_Count loop
      Put_Line(Standard_Error,"[Server] Argument" & Integer'Image(I) & " : " &
                            Ada.Command_Line.Argument (I));
   end loop;
   delay 25.0;

   loop
      Get_Line(line, last);
      if last > 0 then
         ind := index(line(line'first .. last), string'(":"), line'first);
         if ind /= 0 then
            Put_Line("response #" & line(ind+1..last));
         else
            Put_Line("response unknow");
         end if;
      end if;
      delay 0.2;
   end loop;


end Server;
