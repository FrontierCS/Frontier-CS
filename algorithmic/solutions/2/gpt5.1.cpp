#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        // Only possible permutation is [1]
        cout << 1 << " " << 1 << "\n";
        cout.flush();
        return 0;
    }

    vector<int> pos(n + 1, 0); // pos[value] = index
    vector<int> val(n + 1, 0); // val[index] = value

    int pos1 = -1;

    // Step 1: Find positions of 1 and possibly 2
    for (int i = 1; i <= n; i++) {
        vector<int> q(n + 1, 1);
        q[i] = 2; // n >= 2 here

        cout << 0;
        for (int j = 1; j <= n; j++) cout << ' ' << q[j];
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;

        if (x == 0) {
            pos1 = i;
        } else if (x == 2) {
            val[i] = 2;
            pos[2] = i;
        }
    }

    if (pos1 == -1) {
        // Fallback (should not happen): remaining index without value 2 is pos1
        for (int i = 1; i <= n; i++) {
            if (val[i] != 2) {
                pos1 = i;
                break;
            }
        }
    }

    val[pos1] = 1;
    pos[1] = pos1;

    // Collect unused values
    vector<int> unused;
    for (int v = 1; v <= n; v++) {
        if (pos[v] == 0) unused.push_back(v);
    }

    // Step 2: Determine remaining positions
    for (int i = 1; i <= n; i++) {
        if (val[i] != 0) continue; // already known

        for (size_t idx = 0; idx < unused.size(); idx++) {
            int v = unused[idx];

            vector<int> q(n + 1, 1);
            q[i] = v;

            cout << 0;
            for (int j = 1; j <= n; j++) cout << ' ' << q[j];
            cout << '\n';
            cout.flush();

            int x;
            if (!(cin >> x)) return 0;

            // For i != pos1, baseline would be 1, so 2 means match at i
            if (x == 2) {
                val[i] = v;
                pos[v] = i;
                unused.erase(unused.begin() + idx);
                break;
            }
        }
    }

    // Output final guess
    cout << 1;
    for (int i = 1; i <= n; i++) cout << ' ' << val[i];
    cout << '\n';
    cout.flush();

    return 0;
}