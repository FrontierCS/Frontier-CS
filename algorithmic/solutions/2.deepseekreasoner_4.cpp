#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    int n;
    cin >> n;

    if (n == 1) {
        // Trivial case
        cout << "1 1" << endl;
        return 0;
    }

    vector<int> perm(n + 1, 0);          // permutation we are building
    vector<bool> known(n + 1, false);    // whether position is known

    // Step 1: find positions of 1 and 2
    int pos1 = -1, pos2 = -1;
    for (int i = 1; i <= n; ++i) {
        // Build query: i-th position = 2, all others = 1
        cout << 0;
        for (int j = 1; j <= n; ++j) {
            if (j == i) cout << " 2";
            else cout << " 1";
        }
        cout << endl;
        cout.flush();

        int resp;
        cin >> resp;
        if (resp == 0) {
            pos1 = i;   // position of value 1
        } else if (resp == 2) {
            pos2 = i;   // position of value 2
        }
    }

    perm[pos1] = 1;
    perm[pos2] = 2;
    known[pos1] = known[pos2] = true;

    // List of unknown positions
    vector<int> unknown;
    for (int i = 1; i <= n; ++i) {
        if (!known[i]) {
            unknown.push_back(i);
        }
    }

    // Step 2: determine the remaining values 3..n
    for (int v = 3; v <= n; ++v) {
        int lo = 0, hi = (int)unknown.size() - 1;
        while (lo < hi) {
            int mid = (lo + hi) / 2;

            // Build query
            vector<int> q(n + 1);
            // First set all unknown positions to 1 (safe value)
            for (int j = 1; j <= n; ++j) {
                if (known[j]) {
                    q[j] = perm[j];
                } else {
                    q[j] = 1;
                }
            }
            // For positions in S (unknown[lo..mid]), set to v
            for (int idx = lo; idx <= mid; ++idx) {
                int j = unknown[idx];
                q[j] = v;
            }

            cout << 0;
            for (int j = 1; j <= n; ++j) {
                cout << " " << q[j];
            }
            cout << endl;
            cout.flush();

            int resp;
            cin >> resp;
            int expected = v - 1;   // matches from known positions
            if (resp == expected + 1) {
                hi = mid;           // v is in S
            } else {
                lo = mid + 1;       // v is not in S
            }
        }

        // Found position for v
        int found = unknown[lo];
        perm[found] = v;
        known[found] = true;
        // Remove found from unknown (swap with last and pop)
        unknown[lo] = unknown.back();
        unknown.pop_back();
    }

    // Output the guessed permutation
    cout << 1;
    for (int i = 1; i <= n; ++i) {
        cout << " " << perm[i];
    }
    cout << endl;

    return 0;
}