#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        if (n == 1) {
            cout << "! 1" << endl;
            cout.flush();
            continue;
        }

        vector<char> mask(n);

        auto askMask = [&](const vector<char> &m) -> int {
            string s(m.begin(), m.end());
            cout << "? " << s << endl;
            cout.flush();
            int res;
            if (!(cin >> res)) exit(0);
            if (res == -1) exit(0);
            return res;
        };

        vector<int> setS;
        vector<bool> inS(n, false);
        setS.push_back(0);
        inS[0] = true;

        fill(mask.begin(), mask.end(), '0');
        for (int v : setS) mask[v] = '1';
        int qS = askMask(mask);  // query for initial S = {1}

        while (qS > 0) {
            // Build list of candidates (vertices not in S)
            vector<int> cand;
            cand.reserve(n);
            for (int i = 0; i < n; ++i)
                if (!inS[i]) cand.push_back(i);

            vector<int> cur = cand;

            // Binary search to find one "near" vertex
            while (cur.size() > 1) {
                int half = (int)cur.size() / 2;
                vector<int> A(cur.begin(), cur.begin() + half);

                // Query T = A
                fill(mask.begin(), mask.end(), '0');
                for (int v : A) mask[v] = '1';
                int qT = askMask(mask);

                // Query S ∪ A
                fill(mask.begin(), mask.end(), '0');
                for (int v : setS) mask[v] = '1';
                for (int v : A) mask[v] = '1';
                int qST = askMask(mask);

                int I = qS + qT - qST;

                if (I > 0) {
                    cur = A;
                } else {
                    vector<int> B(cur.begin() + half, cur.end());
                    cur.swap(B);
                }
            }

            int v = cur[0];
            inS[v] = true;
            setS.push_back(v);

            // Update qS = query(S) for new S
            fill(mask.begin(), mask.end(), '0');
            for (int x : setS) mask[x] = '1';
            qS = askMask(mask);
        }

        int connected = (int)setS.size() == n ? 1 : 0;
        cout << "! " << connected << endl;
        cout.flush();
    }

    return 0;
}