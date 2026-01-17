#include <bits/stdc++.h>

using namespace std;

int main() {
    int m;
    cin >> m;
    string pos;
    cin >> pos;
    while (true) {
        int k, p;
        string side;
        if (pos == "center") {
            k = 0;
            side = "left";
            p = 0;
        } else {
            k = 1;
            side = "left";
            p = 1;
        }
        cout << k << " " << side << " " << p << endl;
        fflush(stdout);
        cin >> pos;
        if (pos == "treasure") {
            break;
        }
    }
    return 0;
}