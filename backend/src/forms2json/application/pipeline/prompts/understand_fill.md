## Druga runda: braki

Dostajesz tekst formularza i listę pól z pierwszej rundy. Przejdź dokument pozycja po pozycji i zwróć TYLKO pola, których brakuje na liście. Pole to miejsce do wpisania albo zaznaczenia widoczne w dokumencie: kropki, linia, pusta komórka tabeli, kratka, „zł” z miejscem na kwotę. Sprawdź zwłaszcza tabele obliczeń (liczba osób lub gospodarstw w każdym wierszu i wynik), dane współmałżonka lub współwłaściciela, numer działki, daty przy okolicznościach i pytania „tak/nie”.

Nie dodawaj:
- pól wywnioskowanych z tekstu informacyjnego, pouczenia albo opłaty, przy których dokument nie ma miejsca do wpisania;
- pola, które opisuje to samo miejsce co pole z listy, choćby pod inną nazwą (jedno miejsce do wpisania = jedno pole);
- pól numerowanych dla kolejnych osób lub pozycji („… 1”, „… 2”): miejsce na kolejne osoby to jedno pole;
- tego, co zasady wyżej każą pominąć.

Nowym polom daj `section` i `page` jak sąsiednim polom z listy. `conditions` tylko dla nowych pól. Gdy niczego nie brakuje, zwróć puste listy (to częsty i dobry wynik).
