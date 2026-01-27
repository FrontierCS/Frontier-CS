#include <bits/stdc++.h>
using namespace std;

static int queryCount = 0;

static long long tri(long long m) {
    return m * (m + 1) / 2;
}

static long long ask(const vector<int>& idx) {
    ++queryCount;
    if (queryCount > 200) exit(0);
    cout << "0 " << idx.size();
    for (int x : idx) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

static vector<int> buildExistDiffQuery(int a, const vector<int>& group) {
    vector<int> q;
    q.reserve(4 * group.size());
    for (int x : group) {
        q.push_back(a);
        q.push_back(x);
        q.push_back(x);
        q.push_back(a);
    }
    return q;
}

static vector<int> buildClassifyQuery(const vector<int>& pos, int closeIdx, const vector<int>& mvals) {
    int t = (int)pos.size();
    vector<int> q;
    int totalLen = 0;
    for (int i = 0; i < t; i++) totalLen += 2 * mvals[i];
    totalLen += max(0, t - 1);
    q.reserve(totalLen);

    for (int j = 0; j < t; j++) {
        int i = pos[j];
        int m = mvals[j];
        for (int rep = 0; rep < m; rep++) {
            q.push_back(i);
            q.push_back(closeIdx);
        }
        if (j != t - 1) q.push_back(closeIdx); // separator ')'
    }
    return q;
}

static vector<int> computeMvals() {
    vector<int> mvals;
    long long sumW = 0;
    int sumLenNoSep = 0;
    while (true) {
        long long need = sumW + 1;
        long long m = (long long)ceill((sqrtl(1.0L + 8.0L * (long double)need) - 1.0L) / 2.0L);
        while (tri(m) <= sumW) m++;

        int newSumLenNoSep = sumLenNoSep + (int)(2 * m);
        int newT = (int)mvals.size() + 1;
        int totalK = newSumLenNoSep + max(0, newT - 1);
        if (totalK > 1000) break;

        mvals.push_back((int)m);
        sumLenNoSep = newSumLenNoSep;
        sumW += tri(m);
    }
    return mvals;
}

static void solveOne(int n, const vector<int>& baseMvals) {
    queryCount = 0;

    int a = 1;
    vector<int> candidates;
    candidates.reserve(max(0, n - 1));
    for (int i = 2; i <= n; i++) candidates.push_back(i);

    vector<int> groupWithOpp;
    for (int start = 0; start < (int)candidates.size(); start += 250) {
        int end = min((int)candidates.size(), start + 250);
        vector<int> group(candidates.begin() + start, candidates.begin() + end);
        long long res = ask(buildExistDiffQuery(a, group));
        if (res > 0) {
            groupWithOpp = move(group);
            break;
        }
    }
    if (groupWithOpp.empty()) exit(0); // should never happen

    vector<int> cand = groupWithOpp;
    while ((int)cand.size() > 1) {
        int mid = (int)cand.size() / 2;
        vector<int> left(cand.begin(), cand.begin() + mid);
        long long res = ask(buildExistDiffQuery(a, left));
        if (res > 0) {
            cand = move(left);
        } else {
            vector<int> right(cand.begin() + mid, cand.end());
            cand = move(right);
        }
    }
    int b = cand[0];

    long long ori = ask(vector<int>{a, b, a, b});
    int openIdx, closeIdx;
    if (ori == 3) { // a='(', b=')'
        openIdx = a;
        closeIdx = b;
    } else if (ori == 1) { // a=')', b='('
        openIdx = b;
        closeIdx = a;
    } else {
        exit(0);
    }

    vector<char> ans(n + 1, '?');
    ans[openIdx] = '(';
    ans[closeIdx] = ')';

    vector<int> unknown;
    unknown.reserve(n - 2);
    for (int i = 1; i <= n; i++) {
        if (i == openIdx || i == closeIdx) continue;
        unknown.push_back(i);
    }

    int chunkSize = (int)baseMvals.size();
    for (int start = 0; start < (int)unknown.size(); start += chunkSize) {
        int t = min(chunkSize, (int)unknown.size() - start);
        vector<int> pos(unknown.begin() + start, unknown.begin() + start + t);

        vector<int> mvals(baseMvals.begin(), baseMvals.begin() + t);
        vector<int> q = buildClassifyQuery(pos, closeIdx, mvals);
        long long res = ask(q);

        for (int j = t - 1; j >= 0; j--) {
            long long w = tri(mvals[j]);
            if (res >= w) {
                ans[pos[j]] = '(';
                res -= w;
            } else {
                ans[pos[j]] = ')';
            }
        }
    }

    string out;
    out.reserve(n);
    for (int i = 1; i <= n; i++) out.push_back(ans[i]);

    cout << "1 " << out << '\n';
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> mvals = computeMvals(); // should be 13 for this construction

    int n;
    if (!(cin >> n)) return 0;
    solveOne(n, mvals);
    return 0;
}