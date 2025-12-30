#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

const int MAXN = 2000 + 5;
const int64 QUERY_LIMIT = 50000;

int n;
int64 k;
int64 cacheVal[MAXN][MAXN];
unsigned char knownVal[MAXN][MAXN];
unsigned char visitedCell[MAXN][MAXN];
int64 queriesUsed = 0;

int64 getVal(int i, int j) {
    if (!knownVal[i][j]) {
        cout << "QUERY " << i << " " << j << endl;
        cout.flush();
        int64 v;
        if (!(cin >> v)) {
            exit(0);
        }
        cacheVal[i][j] = v;
        knownVal[i][j] = 1;
        ++queriesUsed;
    }
    return cacheVal[i][j];
}

void solve_full_read() {
    vector<int64> vals;
    vals.reserve((size_t)n * (size_t)n);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            vals.push_back(getVal(i, j));
        }
    }
    nth_element(vals.begin(), vals.begin() + (k - 1), vals.end());
    int64 ans = vals[(size_t)k - 1];
    cout << "DONE " << ans << endl;
    cout.flush();
}

void solve_BFS_small() {
    struct Node {
        int64 val;
        int x, y;
    };
    struct CmpMin {
        bool operator()(const Node &a, const Node &b) const {
            return a.val > b.val;
        }
    };

    memset(visitedCell, 0, sizeof(visitedCell));

    priority_queue<Node, vector<Node>, CmpMin> pq;
    visitedCell[1][1] = 1;
    int64 v = getVal(1, 1);
    pq.push({v, 1, 1});

    int64 cnt = 0;
    int64 ans = v;

    while (!pq.empty()) {
        Node cur = pq.top();
        pq.pop();
        ++cnt;
        if (cnt == k) {
            ans = cur.val;
            break;
        }
        int i = cur.x;
        int j = cur.y;

        if (i + 1 <= n && !visitedCell[i + 1][j]) {
            visitedCell[i + 1][j] = 1;
            int64 vv = getVal(i + 1, j);
            pq.push({vv, i + 1, j});
        }
        if (j + 1 <= n && !visitedCell[i][j + 1]) {
            visitedCell[i][j + 1] = 1;
            int64 vv = getVal(i, j + 1);
            pq.push({vv, i, j + 1});
        }
    }

    cout << "DONE " << ans << endl;
    cout.flush();
}

void solve_BFS_large() {
    struct Node {
        int64 val;
        int x, y;
    };
    struct CmpMax {
        bool operator()(const Node &a, const Node &b) const {
            return a.val < b.val;
        }
    };

    memset(visitedCell, 0, sizeof(visitedCell));

    priority_queue<Node, vector<Node>, CmpMax> pq;
    visitedCell[n][n] = 1;
    int64 v = getVal(n, n);
    pq.push({v, n, n});

    int64 totalCells = 1LL * n * n;
    int64 target = totalCells - k + 1; // k-th largest
    int64 cnt = 0;
    int64 ans = v;

    while (!pq.empty()) {
        Node cur = pq.top();
        pq.pop();
        ++cnt;
        if (cnt == target) {
            ans = cur.val;
            break;
        }
        int i = cur.x;
        int j = cur.y;

        if (i - 1 >= 1 && !visitedCell[i - 1][j]) {
            visitedCell[i - 1][j] = 1;
            int64 vv = getVal(i - 1, j);
            pq.push({vv, i - 1, j});
        }
        if (j - 1 >= 1 && !visitedCell[i][j - 1]) {
            visitedCell[i][j - 1] = 1;
            int64 vv = getVal(i, j - 1);
            pq.push({vv, i, j - 1});
        }
    }

    cout << "DONE " << ans << endl;
    cout.flush();
}

int64 count_leq(int64 x) {
    int i = n;
    int j = 1;
    int64 cnt = 0;
    while (i >= 1 && j <= n) {
        int64 v = getVal(i, j);
        if (v <= x) {
            cnt += i;
            ++j;
        } else {
            --i;
        }
    }
    return cnt;
}

void solve_binary_search() {
    int64 vMin = getVal(1, 1);
    int64 vMax = getVal(n, n);
    int64 lo = vMin;
    int64 hi = vMax;

    int64 remaining = QUERY_LIMIT - queriesUsed;
    int maxIter = 0;
    if (2 * (int64)n > 0) {
        maxIter = (int)(remaining / (2 * (int64)n));
    }
    if (maxIter > 60) maxIter = 60;

    while (lo < hi && maxIter > 0) {
        int64 mid = lo + (hi - lo) / 2;
        int64 cnt = count_leq(mid);
        if (cnt >= k) hi = mid;
        else lo = mid + 1;
        --maxIter;
    }

    int64 ans = lo;
    cout << "DONE " << ans << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) {
        return 0;
    }

    int64 totalCells = 1LL * n * n;

    if (totalCells <= QUERY_LIMIT) {
        solve_full_read();
    } else {
        int64 side1 = k;
        int64 side2 = totalCells - k + 1;
        int64 minSide = min(side1, side2);
        if (2 * minSide <= QUERY_LIMIT) {
            if (side1 <= side2) {
                solve_BFS_small();
            } else {
                solve_BFS_large();
            }
        } else {
            solve_binary_search();
        }
    }

    return 0;
}