tell process "System Settings"
    click menu item "Notifications" of menu "View" of menu bar 1
    delay 1
    
    set notificationApp to "Shortwave"
    
    repeat with row in (rows of table 1 of scroll area 1 of group 1 of window 1)
        if value of text field 1 of row is equal to notificationApp then
            select row
            exit repeat
        end if
    end repeat
    delay 1
        
    click radio button "Banners" of radio group 1 of group 1 of window 1
end tell