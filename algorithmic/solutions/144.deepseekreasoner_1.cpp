#include <bits/stdc++.h>
using namespace std;

pair<int, int> query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
}

int main() {
    int n;
    cin >> n;
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);
    auto [M1, M2] = query(all);

    int a = -1, b = -1;
    int med1 = -1, med2 = -1;
    bool found_pair = false;

    // First candidate: index 1
    int candidate = 1;
    for (int i = 2; i <= n; ++i) {
        vector<int> q;
        for (int j = 1; j <= n; ++j)
            if (j != candidate && j != i)
                q.push_back(j);
        auto [m1, m2] = query(q);
        if (m1 == M1 && m2 == M2) {
            a = candidate;
            b = i;
            found_pair = true;
            break;
        }
    }
    if (!found_pair) {
        med1 = candidate;
        // Look for second candidate (not med1)
        for (int cand2 = 2; cand2 <= n; ++cand2) {
            if (cand2 == med1) continue;
            bool pair_found = false;
            for (int i = 1; i <= n; ++i) {
                if (i == cand2 || i == med1) continue;
                vector<int> q;
                for (int j = 1; j <= n; ++j)
                    if (j != cand2 && j != i)
                        q.push_back(j);
                auto [m1, m2] = query(q);
                if (m1 == M1 && m2 == M2) {
                    a = cand2;
                    b = i;
                    pair_found = true;
                    break;
                }
            }
            if (pair_found) {
                found_pair = true;
                break;
            } else {
                med2 = cand2;
                break;
            }
        }
    }

    if (found_pair) {
        vector<int> medians;
        for (int i = 1; i <= n; ++i) {
            if (i == a || i == b) continue;
            vector<int> q1, q2;
            for (int j = 1; j <= n; ++j) {
                if (j != a && j != i) q1.push_back(j);
                if (j != b && j != i) q2.push_back(j);
            }
            auto [m1a, m2a] = query(q1);
            auto [m1b, m2b] = query(q2);
            if ((m1a != M1 || m2a != M2) && (m1b != M1 || m2b != M2))
                medians.push_back(i);
        }
        med1 = medians[0];
        med2 = medians[1];
    }

    cout << "1 " << med1 << " " << med2 << endl;
    cout.flush();
    return 0;
}