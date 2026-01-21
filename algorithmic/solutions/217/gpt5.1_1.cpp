#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int L = N * M;

    vector<char> assigned(L + 1, 0);

    for (int stick = 0; stick < M; ++stick) {
        // Build list of unassigned indices
        vector<int> U;
        U.reserve(L - stick * N);
        for (int i = 1; i <= L; ++i) {
            if (!assigned[i]) U.push_back(i);
        }

        int curSize = (int)U.size();
        vector<char> inA(L + 1, 0);
        for (int x : U) inA[x] = 1;

        vector<int> cand = U; // snapshot order
        vector<int> B;
        B.reserve(curSize);

        // Elimination pass
        for (int x : cand) {
            if (!inA[x]) continue;

            B.clear();
            for (int y : U) {
                if (inA[y] && y != x) B.push_back(y);
            }

            cout << "? " << B.size();
            for (int y : B) cout << " " << y;
            cout << endl;
            cout.flush();

            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;

            if (ans >= 1) {
                inA[x] = 0;
                --curSize;
            }
        }

        // Collect remaining indices in A -> one beautiful stick
        vector<int> S;
        S.reserve(N);
        for (int x : U) {
            if (inA[x]) S.push_back(x);
        }

        cout << "!";
        for (int x : S) cout << " " << x;
        cout << endl;
        cout.flush();

        for (int x : S) assigned[x] = 1;
    }

    return 0;
}