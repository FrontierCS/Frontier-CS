#include <bits/stdc++.h>
using namespace std;

static int queryCount = 0;

static long long ask(const vector<int>& idx) {
    ++queryCount;
    if (queryCount > 200) exit(0);

    cout << "0 " << idx.size();
    for (int x : idx) cout << " " << x;
    cout << endl;
    cout.flush();

    long long ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static long long askPair(int i, int j) {
    vector<int> q = {i, j};
    return ask(q);
}

static long long askDup(const vector<int>& v) {
    vector<int> q;
    q.reserve((int)v.size() * 2);
    for (int x : v) q.push_back(x);
    for (int x : v) q.push_back(x);
    return ask(q);
}

static pair<int,int> findDifferentPairWithin(vector<int> S) {
    // S size <= 500 and contains both types
    while (S.size() > 2) {
        int m = (int)S.size();
        int aSize = (m + 1) / 2; // ceil(m/2)
        vector<int> A(S.begin(), S.begin() + aSize);
        vector<int> B(S.begin() + aSize, S.end());

        long long rA = askDup(A);
        if (rA > 0) {
            S.swap(A);
        } else {
            vector<int> Snew;
            Snew.reserve(1 + (int)B.size());
            Snew.push_back(A[0]);
            for (int x : B) Snew.push_back(x);
            S.swap(Snew);
        }
    }

    int x = S[0], y = S[1];
    long long rxy = askPair(x, y);
    if (rxy == 1) return {x, y}; // x='(', y=')'
    else return {y, x};          // y='(', x=')'
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> left, right;
    int mid = n / 2;
    for (int i = 1; i <= mid; i++) left.push_back(i);
    for (int i = mid + 1; i <= n; i++) right.push_back(i);

    long long qL = 0, qR = 0;
    if (!left.empty()) qL = askDup(left);
    if (!right.empty()) qR = askDup(right);

    int openIdx = -1, closeIdx = -1;

    if (qL > 0) {
        auto pr = findDifferentPairWithin(left);
        openIdx = pr.first;
        closeIdx = pr.second;
    } else if (qR > 0) {
        auto pr = findDifferentPairWithin(right);
        openIdx = pr.first;
        closeIdx = pr.second;
    } else {
        // Both halves uniform; since overall has both types, halves are opposite.
        int a = left[0];
        int b = right[0];
        long long rab = askPair(a, b);
        if (rab == 1) {
            openIdx = a;
            closeIdx = b;
        } else {
            openIdx = b;
            closeIdx = a;
        }
    }

    vector<char> res(n + 1, '?');
    res[closeIdx] = ')';

    vector<int> candidates;
    candidates.reserve(n - 1);
    for (int i = 1; i <= n; i++) if (i != closeIdx) candidates.push_back(i);

    for (int pos = 0; pos < (int)candidates.size(); pos += 8) {
        int g = min(8, (int)candidates.size() - pos);
        vector<int> idxs;
        idxs.reserve(g);
        for (int j = 0; j < g; j++) idxs.push_back(candidates[pos + j]);

        vector<int> q;
        int totalCoeff = (1 << g) - 1;
        q.reserve(3 * totalCoeff);

        for (int j = 0; j < g; j++) {
            int coeff = 1 << j;
            for (int rep = 0; rep < coeff; rep++) {
                q.push_back(closeIdx);
                q.push_back(idxs[j]);
                q.push_back(closeIdx);
            }
        }

        long long ans = ask(q);

        for (int j = 0; j < g; j++) {
            if ((ans >> j) & 1LL) res[idxs[j]] = '(';
            else res[idxs[j]] = ')';
        }
    }

    // closeIdx already set. (openIdx set by decoding; if it happened to be closeIdx, impossible)
    cout << "1 ";
    for (int i = 1; i <= n; i++) cout << res[i];
    cout << endl;
    cout.flush();

    return 0;
}