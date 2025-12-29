#include <iostream>
#include <string>
#include <vector>

using namespace std;

int main() {
    // 1. Initialization: Transform S to I to setup ^ marker
    cout << "S=I" << endl;

    // 2. Success Condition: If ? sees a token (1,2,3) or start (^) on left, match found
    cout << "1?=(return)1" << endl;
    cout << "2?=(return)1" << endl;
    cout << "3?=(return)1" << endl;
    cout << "^?=(return)1" << endl;

    // 3. Bubbling: Move Upper chars (A,B,C) right past tokens (1,2,3) to reach ?
    string upper = "ABC";
    string tokens = "123";
    for(char u : upper) {
        for(char t : tokens) {
            cout << u << t << "=" << t << u << endl;
        }
    }

    // 4. Matching: Upper ? Lower -> Token ?
    cout << "A?a=1?" << endl;
    cout << "B?b=2?" << endl;
    cout << "C?c=3?" << endl;

    // 5. Mismatch Handling: Upper ? WrongLower -> % (Reset)
    string lower = "abc"; // $ handled separately or included? A?$ means mismatch
    string lower_with_end = "abc$";
    for(char l : lower_with_end) {
        if(l == 'a') continue;
        cout << "A?" << l << "=%A" << l << endl;
    }
    for(char l : lower_with_end) {
        if(l == 'b') continue;
        cout << "B?" << l << "=%B" << l << endl;
    }
    for(char l : lower_with_end) {
        if(l == 'c') continue;
        cout << "C?" << l << "=%C" << l << endl;
    }

    // 6. Reset Logic: % moves left, restoring tokens
    cout << "%A=A%" << endl;
    cout << "%B=B%" << endl;
    cout << "%C=C%" << endl;
    cout << "%1=A%a" << endl;
    cout << "%2=B%b" << endl;
    cout << "%3=C%c" << endl;

    // 7. Start Delete: When % reaches start, become D
    cout << "^%=^D" << endl;

    // 8. Delete Logic: D moves right through T to delete first char of s
    cout << "DA=AD" << endl;
    cout << "DB=BD" << endl;
    cout << "DC=CD" << endl;
    cout << "Da=?" << endl;
    cout << "Db=?" << endl;
    cout << "Dc=?" << endl;
    cout << "D$=(return)0" << endl; // s empty

    // 9. Initialization Phase Logic
    cout << "aI=Ia" << endl;
    cout << "bI=Ib" << endl;
    cout << "cI=Ic" << endl;
    cout << "I=^J" << endl;
    cout << "Ja=aJ" << endl;
    cout << "Jb=bJ" << endl;
    cout << "Jc=cJ" << endl;
    cout << "J=R" << endl; // Becomes R (Reverse Separator)

    // 10. Reverse T Phase: Ra -> fa R, move fa left, deposit A, return <
    cout << "Ra=faR" << endl;
    cout << "Rb=fbR" << endl;
    cout << "Rc=fcR" << endl;

    cout << "afa=faa" << endl; cout << "bfa=fab" << endl; cout << "cfa=fac" << endl;
    cout << "afb=fba" << endl; cout << "bfb=fbb" << endl; cout << "cfb=fbc" << endl;
    cout << "afc=fca" << endl; cout << "bfc=fcb" << endl; cout << "cfc=fcc" << endl;

    cout << "^fa=^A<" << endl;
    cout << "^fb=^B<" << endl;
    cout << "^fc=^C<" << endl;

    cout << "<a=a<" << endl; cout << "<b=b<" << endl; cout << "<c=c<" << endl;
    cout << "<R=R" << endl;

    // 11. End Reverse: R becomes $
    cout << "R=$" << endl;

    // 12. Insert ? at boundary (Upper-Lower and ^-Lower)
    for(char u : upper) {
        for(char l : lower_with_end) {
            cout << u << l << "=" << u << "?" << l << endl;
        }
    }
    for(char l : lower) {
        cout << "^" << l << "=^?" << l << endl;
    }
    cout << "^$=(return)1" << endl;

    return 0;
}