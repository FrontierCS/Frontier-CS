#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    auto ask = [&](const vector<int>& v) -> int {
        cout << "?";
        for (int x : v) cout << " " << x;
        cout << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    };

    while (t--) {
        int n;
        cin >> n;
        int N = n * n;
        int k = n - 1;

        // Step 1: Find bottom k = n-1 elements using streaming algorithm
        vector<int> S;
        S.reserve(k);
        for (int i = 1; i <= k; ++i) S.push_back(i);

        for (int x = k + 1; x <= N; ++x) {
            vector<int> q = S;
            q.push_back(x); // size n
            int w = ask(q);
            if (w != x) {
                // replace w in S with x
                for (int i = 0; i < (int)S.size(); ++i) {
                    if (S[i] == w) {
                        S[i] = x;
                        break;
                    }
                }
            }
        }

        // Step 2: Sort the remaining N - (n-1) elements in descending order using comparisons with fillers from S
        vector<char> isBottom(N + 1, false);
        for (int b : S) isBottom[b] = true;
        vector<int> T;
        T.reserve(N - k);
        for (int i = 1; i <= N; ++i) if (!isBottom[i]) T.push_back(i);

        vector<int> F;
        if (n >= 2) {
            // use any n-2 elements from S as fillers
            for (int i = 0; i < n - 2; ++i) F.push_back(S[i]);
        }

        auto cmp = [&](int a, int b) -> bool {
            if (a == b) return false;
            vector<int> q = F;
            q.push_back(a);
            q.push_back(b);
            int w = ask(q);
            return w == a; // a faster than b
        };

        sort(T.begin(), T.end(), cmp);

        // Output in descending order
        cout << "!";
        for (int x : T) cout << " " << x;
        cout << endl;
        cout.flush();
    }
    return 0;
}