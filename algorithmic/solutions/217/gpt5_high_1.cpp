#include <bits/stdc++.h>
using namespace std;

int N, M, L;

int ask(const vector<int>& S) {
    cout << "? " << (int)S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

vector<int> shrink_to_one(const vector<int>& pool, int N, vector<int>& mark, int& markCounter) {
    vector<int> S = pool;
    while ((int)S.size() > N) {
        if ((int)S.size() > 2 * N) {
            vector<int> snap = S;
            int k = min(2 * N, (int)snap.size());
            int s = (int)snap.size();
            int base = s / k, rem = s % k;
            int idx = 0;
            for (int i = 0; i < k && (int)S.size() > 2 * N; ++i) {
                int cur = base + (i < rem ? 1 : 0);
                int curMark = ++markCounter;
                if (markCounter >= INT_MAX / 2) {
                    fill(mark.begin(), mark.end(), 0);
                    markCounter = 1;
                    curMark = 1;
                }
                for (int j = 0; j < cur; ++j) {
                    int v = snap[idx++];
                    if (v >= 1 && v <= L) mark[v] = curMark;
                }
                vector<int> T;
                T.reserve(S.size());
                for (int v : S) if (mark[v] != curMark) T.push_back(v);
                if (ask(T) >= 1) {
                    S.swap(T);
                }
            }
        } else {
            for (size_t i = 0; i < S.size() && (int)S.size() > N; ) {
                vector<int> T;
                T.reserve(S.size() - 1);
                T.insert(T.end(), S.begin(), S.begin() + i);
                T.insert(T.end(), S.begin() + i + 1, S.end());
                if (ask(T) >= 1) {
                    S.swap(T);
                } else {
                    ++i;
                }
            }
        }
    }
    return S;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) return 0;
    L = N * M;

    vector<int> unused(L);
    iota(unused.begin(), unused.end(), 1);

    vector<int> mark(L + 1, 0);
    int markCounter = 0;

    for (int t = 0; t < M; ++t) {
        vector<int> S = shrink_to_one(unused, N, mark, markCounter);

        cout << "! ";
        for (int i = 0; i < N; ++i) {
            if (i) cout << " ";
            cout << S[i];
        }
        cout << endl;
        cout.flush();

        // Remove used indices from 'unused'
        vector<char> usedFlag(L + 1, 0);
        for (int v : S) if (v >= 1 && v <= L) usedFlag[v] = 1;
        vector<int> newUnused;
        newUnused.reserve(unused.size() - N);
        for (int v : unused) if (!usedFlag[v]) newUnused.push_back(v);
        unused.swap(newUnused);
    }
    return 0;
}