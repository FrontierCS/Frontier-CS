#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

void answer(int x) {
    cout << "! " << x << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<int> A(n + 1, -1), B(n + 1, -1);
        // Ask all i -> 1 (i != 1)
        for (int i = 2; i <= n; ++i) {
            A[i] = ask(i, 1);
        }
        // Ask 1 -> j (j != 1)
        for (int j = 2; j <= n; ++j) {
            B[j] = ask(1, j);
        }

        int requiredKnights = (3 * n) / 10 + 1;

        int impostorIndex = -1;
        bool found = false;

        for (int x = 0; x <= 1; ++x) {      // R_1
            for (int y = 0; y <= 1; ++y) {  // S_1
                vector<int> R(n + 1), S(n + 1);
                R[1] = x;
                S[1] = y;
                for (int i = 2; i <= n; ++i) R[i] = y ^ (1 - A[i]);  // R_i = S_1 XOR !A_i
                for (int j = 2; j <= n; ++j) S[j] = x ^ (1 - B[j]);  // S_j = R_1 XOR !B_j

                bool invalid = false;
                int knights = 0, impostors = 0, impIdx = -1;

                for (int i = 1; i <= n; ++i) {
                    if (R[i] == 1 && S[i] == 0) { // invalid combination
                        invalid = true;
                        break;
                    }
                    if (R[i] == 1 && S[i] == 1) knights++;
                    else if (R[i] == 0 && S[i] == 1) {
                        impostors++;
                        impIdx = i;
                    }
                    // R=0,S=0 are knaves, allowed
                }
                if (invalid) continue;
                if (impostors != 1) continue;
                if (knights < requiredKnights) continue;

                // Valid assignment found
                impostorIndex = impIdx;
                found = true;
                break;
            }
            if (found) break;
        }

        if (!found) {
            // Fallback (shouldn't happen): pick 1
            impostorIndex = 1;
        }

        answer(impostorIndex);
    }
    return 0;
}