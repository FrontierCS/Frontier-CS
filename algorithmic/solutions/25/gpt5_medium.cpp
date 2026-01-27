#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        int n;
        if(!(cin >> n)) return 0;
        auto ask = [&](const string &s) -> int {
            cout << "? " << s << endl;
            cout.flush();
            int res;
            if(!(cin >> res)) exit(0);
            return res;
        };
        auto answer = [&](int x){
            cout << "! " << x << endl;
            cout.flush();
        };
        if (n <= 1) {
            answer(1);
            continue;
        }
        bool disconnected = false;
        // Check isolated vertices via singleton queries
        for (int i = 0; i < n; ++i) {
            string s(n, '0');
            s[i] = '1';
            int res = ask(s);
            if (res == -1) return 0;
            if (res == 0) disconnected = true;
        }
        if (disconnected) {
            answer(0);
            continue;
        }
        // Random probing: try random subsets to catch union-of-components (zero boundary)
        // If any query returns zero, graph is disconnected.
        // Limit number of random queries to stay well within 3500.
        mt19937 rng(712367);
        int trials = 1000;
        for (int t = 0; t < trials && !disconnected; ++t) {
            string s(n, '0');
            for (int i = 0; i < n; ++i) {
                s[i] = (uniform_int_distribution<int>(0,1)(rng) ? '1' : '0');
            }
            // ensure neither empty nor full to avoid trivial zeros
            if (count(s.begin(), s.end(), '1') == 0 || count(s.begin(), s.end(), '1') == n) {
                int pos = uniform_int_distribution<int>(0, n-1)(rng);
                s[pos] = (s[pos] == '1' ? '0' : '1');
            }
            int res = ask(s);
            if (res == -1) return 0;
            if (res == 0) {
                disconnected = true;
                break;
            }
        }
        answer(disconnected ? 0 : 1);
    }
    return 0;
}