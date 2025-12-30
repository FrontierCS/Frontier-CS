#include <bits/stdc++.h>
using namespace std;

static int n;
static long long l1_lim, l2_lim;
static long long qcnt = 0, scnt = 0;

static vector<int> who; // who[pos] = piece id currently at pos (piece ids are 1..n)

static void die() {
    exit(0);
}

static int askSeg(int l, int r) {
    if (l > r) die();
    if (qcnt + 1 > l1_lim) {
        // Likely will get -1 from judge; avoid desync by exiting.
        die();
    }
    cout << "1 " << l << " " << r << '\n';
    cout.flush();
    int x;
    if (!(cin >> x)) die();
    if (x < 0) die();
    ++qcnt;
    return x;
}

static void doSwap(int i, int j) {
    if (i == j) return;
    if (scnt + 1 > l2_lim) {
        die();
    }
    cout << "2 " << i << " " << j << '\n';
    cout.flush();
    int ok;
    if (!(cin >> ok)) die();
    if (ok < 0) die();
    ++scnt;
    swap(who[i], who[j]);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> l1_lim >> l2_lim)) return 0;

    who.assign(n + 1, 0);
    for (int i = 1; i <= n; i++) who[i] = i;

    if (n == 1) {
        cout << "3 1\n";
        cout.flush();
        return 0;
    }

    // Find an endpoint piece: place candidate at position 1, query segments of positions [2..n].
    // If candidate is endpoint (value 1 or n), remaining values are contiguous => segments = 1; else 2.
    bool found = false;
    for (int i = 1; i <= n; i++) {
        if (i != 1) doSwap(1, i);
        int seg = askSeg(2, n);
        if (seg == 1) {
            found = true;
            break; // keep endpoint at position 1
        }
        if (i != 1) doSwap(1, i); // revert
    }
    if (!found) die();

    vector<int> order;
    order.reserve(n);
    order.push_back(who[1]);

    int m = n - 1; // number of unvisited pieces; they occupy positions [2..m+1]
    while (m > 0) {
        int posNeighbor = 2;
        if (m > 1) {
            int lo = 2, hi = m + 1;
            while (lo < hi) {
                int mid = (lo + hi) >> 1;
                int s1 = askSeg(1, mid);
                int s2 = askSeg(2, mid);
                // Current piece at position 1 is an endpoint in remaining graph, so:
                // if its (unique) neighbor is inside [2..mid], adding it doesn't increase components -> s1 == s2
                if (s1 == s2) hi = mid;
                else lo = mid + 1;
            }
            posNeighbor = lo;
        }

        int nextPiece = who[posNeighbor];

        // Move nextPiece to position 1 (becomes current)
        doSwap(1, posNeighbor);

        // Remove old current (now at posNeighbor) from unvisited block by swapping to the end
        int endPos = m + 1;
        if (posNeighbor != endPos) doSwap(posNeighbor, endPos);

        m--;
        order.push_back(nextPiece);
    }

    vector<int> valOfPiece(n + 1, 0);
    for (int i = 0; i < n; i++) valOfPiece[order[i]] = i + 1;

    cout << "3";
    for (int pos = 1; pos <= n; pos++) {
        cout << ' ' << valOfPiece[who[pos]];
    }
    cout << '\n';
    cout.flush();
    return 0;
}