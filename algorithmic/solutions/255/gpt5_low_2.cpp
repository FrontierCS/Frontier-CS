#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if(!(cin >> t)) return 0;
    while(t--) {
        int n;
        cin >> n;

        auto ask = [&](int i, int j) -> int {
            cout << "? 1 1\n" << i << "\n" << j << "\n" << flush;
            int F;
            if(!(cin >> F)) exit(0);
            return F;
        };

        int a = -1;

        // Try to find one non-zero magnet
        // First attempt with base 1
        bool found = false;
        for(int i = 2; i <= n; ++i) {
            int f = ask(1, i);
            if(f != 0) {
                a = 1;
                found = true;
                break;
            }
        }
        if(!found) {
            // base 1 is zero, search pair among 2..n
            bool ok = false;
            for(int i = 2; i <= n && !ok; ++i) {
                for(int j = i + 1; j <= n; ++j) {
                    int f = ask(i, j);
                    if(f != 0) {
                        a = i;
                        ok = true;
                        break;
                    }
                }
            }
            if(!ok) {
                // Should not happen due to constraints (at least two non-zero)
                a = 2; // fallback
            }
        }

        // Now a is a known non-zero index
        vector<int> zeros;
        for(int i = 1; i <= n; ++i) {
            if(i == a) continue;
            int f = ask(i, a);
            if(f == 0) zeros.push_back(i);
        }

        cout << "! " << zeros.size();
        for(int x : zeros) cout << " " << x;
        cout << "\n" << flush;
    }
    return 0;
}