#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    int qcnt = 0;
    unordered_map<string, int> cacheF; // mask -> |F(S)| = |S| + query(S)
    vector<int> f_single;              // |F({v})|
    vector<int> rem;                   // remaining vertices (0-based)
    vector<int> pos;                   // position in rem or -1
    string maskR;                      // current reached set mask
    int szR = 0;                       // |R|
    int fR = 0;                        // |F(R)|

    int queryBoundary(const string& mask) {
        cout << "? " << mask << "\n";
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        ++qcnt;
        return ans;
    }

    int queryF(const string& mask, int ones) {
        auto it = cacheF.find(mask);
        if (it != cacheF.end()) return it->second;
        int b = queryBoundary(mask);
        int f = ones + b;
        cacheF.emplace(mask, f);
        return f;
    }

    bool hasAdjInterval(int l, int r) {
        int k = r - l;
        if (k <= 0) return false;
        if (k == 1) {
            int u = rem[l];
            string um = maskR;
            um[u] = '1';
            int fRu = queryF(um, szR + 1);
            long long inter = (long long)fR + f_single[u] - fRu;
            return inter > 0;
        }

        string mx(n, '0');
        for (int i = l; i < r; i++) mx[rem[i]] = '1';
        int fX = queryF(mx, k);

        string um = maskR;
        for (int i = l; i < r; i++) um[rem[i]] = '1';
        int fRX = queryF(um, szR + k);

        long long inter = (long long)fR + fX - fRX;
        return inter > 0;
    }

    int findCandidateIndex() {
        int l = 0, r = (int)rem.size();
        while (r - l > 1) {
            int mid = (l + r) / 2;
            if (hasAdjInterval(l, mid)) r = mid;
            else l = mid;
        }
        return l;
    }

    void removeFromRem(int v) {
        int idx = pos[v];
        int last = rem.back();
        rem[idx] = last;
        pos[last] = idx;
        rem.pop_back();
        pos[v] = -1;
    }

    void run() {
        cin >> n;
        cacheF.reserve(8000);

        if (n == 1) {
            // Still need to respect interactive format: no queries required.
            cout << "! 1\n";
            cout.flush();
            return;
        }

        f_single.assign(n, 0);
        for (int i = 0; i < n; i++) {
            string m(n, '0');
            m[i] = '1';
            f_single[i] = queryF(m, 1);
        }

        maskR.assign(n, '0');
        maskR[0] = '1';
        szR = 1;
        fR = f_single[0];

        rem.clear();
        pos.assign(n, -1);
        for (int i = 1; i < n; i++) {
            pos[i] = (int)rem.size();
            rem.push_back(i);
        }

        while (!rem.empty()) {
            int idx = findCandidateIndex();
            int u = rem[idx];

            string um = maskR;
            um[u] = '1';
            int fRu = queryF(um, szR + 1);
            long long inter = (long long)fR + f_single[u] - fRu;

            if (inter <= 0) break; // no vertex within distance <= 2 from R

            maskR[u] = '1';
            szR++;
            fR = fRu;
            removeFromRem(u);

            if (qcnt > 3500) exit(0);
        }

        cout << "! " << (szR == n ? 1 : 0) << "\n";
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        Solver s;
        s.run();
    }
    return 0;
}