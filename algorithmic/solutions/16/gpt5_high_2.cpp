#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        long long n;
        cin >> n;
        long long u = 1, v = (n >= 3 ? 3 : 2);
        cout << "! " << u << " " << v << "\n";
        cout.flush();
    }
    return 0;
}