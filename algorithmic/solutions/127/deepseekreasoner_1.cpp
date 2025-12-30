#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

bool query(int i, int &a0, int &a1) {
    cout << "? " << i << endl;
    cout.flush();
    cin >> a0 >> a1;
    return (a0 + a1) == 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    int l = 0, r = n - 1;
    int a0, a1;

    // query left end
    if (query(l, a0, a1)) {
        cout << "! " << l << endl;
        return 0;
    }
    // diamond is strictly right of l
    ++l;

    // query right end
    if (query(r, a0, a1)) {
        cout << "! " << r << endl;
        return 0;
    }
    // diamond is strictly left of r
    --r;

    // if interval collapsed, the only index left is the diamond
    if (l > r) {
        // l-1 or r+1? Actually diamond must be between original l and r.
        // After moving l right and r left, if they cross, the diamond is at the only index.
        // For n=3: indices 0,1,2. Query 0 -> diamond right -> l=1. Query 2 -> diamond left -> r=1.
        // So l=1,r=1, not crossed. So l>r only if n=2? But n>=3.
        // So we shouldn't get here, but fallback.
        cout << "! " << l << endl;
        return 0;
    }
    if (l == r) {
        cout << "! " << l << endl;
        return 0;
    }

    const int TH = 1000;   // threshold for linear scan
    const int M = 10;      // number of internal points per iteration

    while (r - l > TH) {
        int step = (r - l) / (M + 1);
        if (step == 0) break;

        vector<int> indices;
        for (int i = 1; i <= M; ++i) {
            int idx = l + i * step;
            if (idx > r) break;
            indices.push_back(idx);
        }

        int p = -1; // rightmost index with a0 == 0
        int q = -1; // leftmost index with a1 == 0
        bool found = false;

        for (int idx : indices) {
            if (query(idx, a0, a1)) {
                cout << "! " << idx << endl;
                return 0;
            }
            if (a0 == 0) p = max(p, idx);
            if (a1 == 0) {
                if (q == -1) q = idx;
                else q = min(q, idx);
            }
        }

        if (p != -1) l = p + 1;
        if (q != -1) r = q - 1;

        if (p == -1 && q == -1) {
            // no decisive point -> interval is small (inside expensive cluster)
            break;
        }

        if (l > r) {
            // diamond must be at the only index between p and q
            // actually p and q are not consecutive, so l == r in this case
            cout << "! " << l << endl;
            return 0;
        }
        if (l == r) {
            cout << "! " << l << endl;
            return 0;
        }
    }

    // linear scan of the remaining interval
    for (int i = l; i <= r; ++i) {
        if (query(i, a0, a1)) {
            cout << "! " << i << endl;
            return 0;
        }
    }

    // fallback (should not happen)
    cout << "! " << l << endl;
    return 0;
}