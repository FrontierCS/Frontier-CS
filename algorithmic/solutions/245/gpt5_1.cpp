#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int _ = 0; _ < t; ++_) {
        int n;
        if (!(cin >> n)) return 0;
        cin >> ws;
        int p = cin.peek();
        if (p == 'K' || p == 'k' || p == 'N' || p == 'n' || p == 'I' || p == 'i') {
            // Roles string variant
            vector<char> roles;
            roles.reserve(n);
            while ((int)roles.size() < n) {
                char ch;
                if (!(cin >> ch)) return 0;
                if (ch == 'K' || ch == 'k' || ch == 'N' || ch == 'n' || ch == 'I' || ch == 'i') {
                    roles.push_back(ch);
                }
            }
            int idx = 1;
            for (int i = 0; i < n; ++i) {
                char ch = toupper(roles[i]);
                if (ch == 'I') {
                    idx = i + 1;
                    break;
                }
            }
            cout << idx << '\n';
        } else {
            // Bits (answers) variant: read 2*(n-1) bits corresponding to queries (? 1 i) and (? i 1) for i=2..n
            auto getBit = [&]() -> int {
                char c;
                while (cin.get(c)) {
                    if (c == '0' || c == '1') return c - '0';
                    // ignore other characters (whitespace or unexpected)
                }
                return -1;
            };
            vector<int> v(n + 1, 0);
            int countOnes = 0;
            for (int i = 2; i <= n; ++i) {
                int a1i = getBit();
                if (a1i == -1) return 0;
                int ai1 = getBit();
                if (ai1 == -1) return 0;
                int vi = a1i ^ ai1;
                v[i] = vi;
                if (vi) ++countOnes;
            }
            int imp = 1;
            if (countOnes != n - 1) {
                for (int i = 2; i <= n; ++i) {
                    if (v[i]) { imp = i; break; }
                }
            }
            cout << imp << '\n';
        }
    }
    return 0;
}