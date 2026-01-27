#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if(!(cin >> n)) return 0;

    long long la = 1, lb = 1;
    while (true) {
        cout << la << " " << lb << endl;
        cout.flush();
        int r;
        if(!(cin >> r)) return 0;
        if (r == 0) break;
        if (r == 1) {
            if (la < n) la++;
        } else if (r == 2) {
            if (lb < n) lb++;
        } else if (r == 3) {
            // This should not happen for query (la, lb) since x<=a and y<=b always.
            // As a fallback, try to move conservatively.
            if (la < n) la++;
            else if (lb < n) lb++;
        }
    }
    return 0;
}