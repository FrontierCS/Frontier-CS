#include <bits/stdc++.h>
using namespace std;

long long ask_pair(int i, int j) {
    cout << "0 2 " << i << ' ' << j << endl;
    cout.flush();
    long long ans;
    if (!(cin >> ans)) {
        exit(0);
    }
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<char> s(n + 1, '?');

    int openIdx = -1;

    // Step 1: find one '(' and one ')' using pair queries
    for (int i = 1; i <= n && openIdx == -1; ++i) {
        for (int j = i + 1; j <= n && openIdx == -1; ++j) {
            long long a1 = ask_pair(i, j);
            if (a1 == 1) {
                s[i] = '(';
                s[j] = ')';
                openIdx = i;
                break;
            }
            long long a2 = ask_pair(j, i);
            if (a2 == 1) {
                s[j] = '(';
                s[i] = ')';
                openIdx = j;
                break;
            }
        }
    }

    if (openIdx == -1) {
        // Fallback (should not happen with valid interactor):
        // assume first is '(' and deduce rest arbitrarily
        openIdx = 1;
        s[openIdx] = '(';
    }

    // Step 2: deduce all other characters using the known '(' at openIdx
    for (int k = 1; k <= n; ++k) {
        if (k == openIdx) continue;
        long long ans = ask_pair(openIdx, k);
        if (ans == 1) {
            s[k] = ')';
        } else {
            s[k] = '(';
        }
    }

    string res;
    res.reserve(n);
    for (int i = 1; i <= n; ++i) res.push_back(s[i]);

    cout << "1 " << res << endl;
    cout.flush();

    return 0;
}