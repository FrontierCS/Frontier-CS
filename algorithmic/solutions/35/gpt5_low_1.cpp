#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n;
        if (!(cin >> n)) return 0;
        int fb;
        if (!(cin >> fb)) return 0;
        if (fb == -1) return 0;
        cout << "! " << 1 << '\n';
        cout.flush();
    }
    return 0;
}