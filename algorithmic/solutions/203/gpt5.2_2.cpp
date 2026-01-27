#include <bits/stdc++.h>
using namespace std;

static int N, M;
static int queryCount = 0;

static vector<int> allX, allY;
static vector<int> markStamp;
static int curStamp = 1;

static int doQuery(const vector<int>& ids) {
    ++queryCount;
    if (queryCount > 20000) exit(0);

    cout << "Query " << (int)ids.size();
    for (int id : ids) cout << ' ' << id;
    cout << '\n';
    cout.flush();

    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

static vector<int> complementOf(const vector<int>& universe, const vector<int>& removed) {
    ++curStamp;
    if (curStamp == INT_MAX) {
        curStamp = 1;
        fill(markStamp.begin(), markStamp.end(), 0);
    }
    for (int id : removed) markStamp[id] = curStamp;
    vector<int> res;
    res.reserve(universe.size());
    for (int id : universe) if (markStamp[id] != curStamp) res.push_back(id);
    return res;
}

// Non-mutual: hit(removed) == true iff removed intersects {mate(x), admirer(x)}
static bool hitRemovedY_nonMutual(int x, const vector<int>& removedY) {
    vector<int> B = complementOf(allY, removedY);
    vector<int> ids = B;
    ids.push_back(x);
    int r = doQuery(ids);
    int k = (int)B.size();
    return r != (k - 1);
}

static bool hitRemovedX_nonMutual(int y, const vector<int>& removedX) {
    vector<int> A = complementOf(allX, removedX);
    vector<int> ids = A;
    ids.push_back(y);
    int r = doQuery(ids);
    int k = (int)A.size();
    return r != (k - 1);
}

static int findOneDefectByRemovedY(int x, vector<int> candidates) {
    while ((int)candidates.size() > 1) {
        int mid = (int)candidates.size() / 2;
        vector<int> half(candidates.begin(), candidates.begin() + mid);
        if (hitRemovedY_nonMutual(x, half)) {
            candidates = std::move(half);
        } else {
            candidates.erase(candidates.begin(), candidates.begin() + mid);
        }
    }
    return candidates[0];
}

static int findOneDefectByRemovedX(int y, vector<int> candidates) {
    while ((int)candidates.size() > 1) {
        int mid = (int)candidates.size() / 2;
        vector<int> half(candidates.begin(), candidates.begin() + mid);
        if (hitRemovedX_nonMutual(y, half)) {
            candidates = std::move(half);
        } else {
            candidates.erase(candidates.begin(), candidates.begin() + mid);
        }
    }
    return candidates[0];
}

static pair<int,int> findTwoDefectsY_nonMutual(int x) {
    int d1 = findOneDefectByRemovedY(x, allY);
    vector<int> remaining;
    remaining.reserve(N - 1);
    for (int y : allY) if (y != d1) remaining.push_back(y);
    int d2 = findOneDefectByRemovedY(x, remaining);
    return {d1, d2};
}

static pair<int,int> findTwoDefectsX_nonMutual(int y) {
    int d1 = findOneDefectByRemovedX(y, allX);
    vector<int> remaining;
    remaining.reserve(N - 1);
    for (int x : allX) if (x != d1) remaining.push_back(x);
    int d2 = findOneDefectByRemovedX(y, remaining);
    return {d1, d2};
}

// Mutual: mate-in-subset oracle
static bool mateInSubsetY_mutual(int x, const vector<int>& subsetY) {
    vector<int> ids = subsetY;
    ids.push_back(x);
    int r = doQuery(ids);
    int k = (int)subsetY.size();
    // mutual case: r == k iff mate is included
    return r == k;
}

static bool mateInSubsetX_mutual(int y, const vector<int>& subsetX) {
    vector<int> ids = subsetX;
    ids.push_back(y);
    int r = doQuery(ids);
    int k = (int)subsetX.size();
    return r == k;
}

static int findMateY_mutual(int x) {
    vector<int> candidates = allY;
    while ((int)candidates.size() > 1) {
        int mid = (int)candidates.size() / 2;
        vector<int> half(candidates.begin(), candidates.begin() + mid);
        if (mateInSubsetY_mutual(x, half)) {
            candidates = std::move(half);
        } else {
            candidates.erase(candidates.begin(), candidates.begin() + mid);
        }
    }
    return candidates[0];
}

static int findMateX_mutual(int y) {
    vector<int> candidates = allX;
    while ((int)candidates.size() > 1) {
        int mid = (int)candidates.size() / 2;
        vector<int> half(candidates.begin(), candidates.begin() + mid);
        if (mateInSubsetX_mutual(y, half)) {
            candidates = std::move(half);
        } else {
            candidates.erase(candidates.begin(), candidates.begin() + mid);
        }
    }
    return candidates[0];
}

static bool containsSmall(const vector<int>& v, int x) {
    for (int a : v) if (a == x) return true;
    return false;
}

static bool dfsKuhn(int x, const vector<vector<int>>& adj, vector<int>& matchY, vector<int>& vis) {
    for (int y : adj[x]) {
        if (vis[y]) continue;
        vis[y] = 1;
        if (matchY[y] == 0 || dfsKuhn(matchY[y], adj, matchY, vis)) {
            matchY[y] = x;
            return true;
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N)) return 0;
    M = 2 * N;

    allX.reserve(N);
    allY.reserve(N);
    for (int i = 1; i <= N; i++) allX.push_back(i);
    for (int i = N + 1; i <= 2 * N; i++) allY.push_back(i);

    markStamp.assign(M + 1, 0);

    vector<char> mutualX(N + 1, 0);
    vector<char> mutualY(M + 1, 0);

    // Detect mutual on X side
    for (int x = 1; x <= N; x++) {
        vector<int> ids = allY;
        ids.push_back(x);
        int r = doQuery(ids);
        mutualX[x] = (r == N);
    }

    // Detect mutual on Y side
    for (int y = N + 1; y <= 2 * N; y++) {
        vector<int> ids = allX;
        ids.push_back(y);
        int r = doQuery(ids);
        mutualY[y] = (r == N);
    }

    vector<vector<int>> candY(N + 1);
    vector<vector<int>> candX(M + 1);

    // Build candidates for X -> Y
    for (int x = 1; x <= N; x++) {
        if (mutualX[x]) {
            int mate = findMateY_mutual(x);
            candY[x] = {mate};
        } else {
            auto [d1, d2] = findTwoDefectsY_nonMutual(x);
            candY[x] = {d1, d2};
        }
    }

    // Build candidates for Y -> X
    for (int y = N + 1; y <= 2 * N; y++) {
        if (mutualY[y]) {
            int mate = findMateX_mutual(y);
            candX[y] = {mate};
        } else {
            auto [d1, d2] = findTwoDefectsX_nonMutual(y);
            candX[y] = {d1, d2};
        }
    }

    // Build reciprocal edges (only mates are reciprocal)
    vector<vector<int>> adj(N + 1);
    for (int x = 1; x <= N; x++) {
        for (int y : candY[x]) {
            if (containsSmall(candX[y], x)) adj[x].push_back(y);
        }
    }

    // Find matching
    vector<int> matchY(M + 1, 0);
    for (int x = 1; x <= N; x++) {
        vector<int> vis(M + 1, 0);
        dfsKuhn(x, adj, matchY, vis);
    }

    vector<int> mateOfX(N + 1, 0);
    for (int y = N + 1; y <= 2 * N; y++) {
        if (matchY[y]) mateOfX[matchY[y]] = y;
    }

    // Output answers
    for (int x = 1; x <= N; x++) {
        int y = mateOfX[x];
        if (y == 0) {
            // Fallback (should not happen): pick any reciprocal candidate
            for (int yy : candY[x]) if (containsSmall(candX[yy], x)) { y = yy; break; }
            if (y == 0) y = candY[x][0];
        }
        cout << "Answer " << x << ' ' << y << '\n';
        cout.flush();
    }

    return 0;
}