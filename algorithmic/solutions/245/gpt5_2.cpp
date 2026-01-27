#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto ask = [&](int i, int j) -> int {
        cout << "? " << i << " " << j << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
        return r;
    };

    auto answer = [&](int x) {
        cout << "! " << x << endl;
        cout.flush();
    };

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        vector<int> D(n + 1, 0), X(n + 1, 0);
        vector<int> ans1(n + 1, -1), ai2(n + 1, -1);

        // Step 1: Get base answers
        int a12 = ask(1, 2); ans1[2] = a12;
        int a13 = ask(1, 3); ans1[3] = a13;

        for (int i = 3; i <= n; ++i) ai2[i] = ask(i, 2);
        int a23 = ask(2, 3);

        // Compute D[i] = L[i] XOR L[1]
        D[1] = 0;
        D[2] = a23 ^ a13;
        for (int i = 3; i <= n; ++i) D[i] = ai2[i] ^ a12;

        // Step 2: Compute X[k] = K[k] XOR L[1]
        for (int k = 4; k <= n; ++k) ans1[k] = ask(1, k);
        X[2] = 1 - a12;
        X[3] = 1 - a13;
        for (int k = 4; k <= n; ++k) X[k] = 1 - ans1[k];

        int a21 = ask(2, 1);
        X[1] = (a21 == 1 ? D[2] : 1 - D[2]);

        // Step 3: Find impostor: unique j with D[j] XOR X[j] == 1
        int impostor = -1;
        for (int j = 1; j <= n; ++j) {
            if ((D[j] ^ X[j]) == 1) {
                impostor = j;
                break;
            }
        }
        if (impostor == -1) impostor = 1; // Fallback, should not happen if consistent

        answer(impostor);
    }

    return 0;
}