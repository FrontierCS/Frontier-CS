#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if(!(cin >> n)) return 0;
    // Fallback trivial interaction: guess 1, then 2 if incorrect.
    cout << "! " << 1 << endl << flush;
    string res;
    if(!(cin >> res)) return 0;
    if(res == ":)") return 0;
    cout << "! " << min(2LL, n) << endl << flush;
    cin >> res;
    return 0;
}