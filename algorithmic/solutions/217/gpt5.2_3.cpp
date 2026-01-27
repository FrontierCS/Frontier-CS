#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int N, M;
    int L;
    mt19937 rng;
    long long Q = 0;

    Solver() : rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count()) {}

    int ask(const vector<int>& idx) {
        cout << "? " << idx.size();
        for (int x : idx) cout << ' ' << x;
        cout << '\n' << flush;
        ++Q;
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
        return r;
    }

    void answer(const vector<int>& stick) {
        cout << "!";
        for (int x : stick) cout << ' ' << x;
        cout << '\n' << flush;
    }

    vector<int> sampleSubset(const vector<int>& S, int k) {
        vector<int> T = S;
        shuffle(T.begin(), T.end(), rng);
        if ((int)T.size() > k) T.resize(k);
        return T;
    }

    void shrinkToN_Block(vector<int>& S) {
        shuffle(S.begin(), S.end(), rng);

        int B = max(1, (int)(S.size() - N) / 2);
        while ((int)S.size() > N) {
            bool removed = false;

            int extra = (int)S.size() - N;
            if (extra <= 0) break;
            if (B > extra) B = extra;
            if (B <= 0) B = 1;

            for (int i = 0; i < (int)S.size() && (int)S.size() > N; ) {
                int block = min(B, (int)S.size() - i);
                if ((int)S.size() - block < N) { i += block; continue; }

                vector<int> T;
                T.reserve(S.size() - block);
                for (int j = 0; j < (int)S.size(); j++) {
                    if (j < i || j >= i + block) T.push_back(S[j]);
                }

                int a = ask(T);
                if (a >= 1) {
                    S.swap(T);
                    removed = true;
                    // Keep i (now points to next element after removed block)
                } else {
                    i += block;
                }
            }

            if (!removed) {
                if (B == 1) break;
                B = max(1, B / 2);
            }
        }

        // Fallback (should rarely be needed)
        int i = 0;
        while ((int)S.size() > N) {
            vector<int> T;
            T.reserve(S.size() - 1);
            for (int j = 0; j < (int)S.size(); j++) if (j != i) T.push_back(S[j]);
            int a = ask(T);
            if (a >= 1) {
                S.swap(T);
                if (i > 0) --i;
            } else {
                ++i;
                if (i >= (int)S.size()) i = 0;
            }
        }
    }

    vector<int> getStick(const vector<int>& remaining, int mRemaining) {
        if ((int)remaining.size() == N) return remaining;

        vector<int> S = remaining;
        int minc = mRemaining;

        int target = min((int)S.size(), 4 * N);

        for (int round = 0; round < 80 && (int)S.size() > target; round++) {
            int sz = (int)S.size();
            double keep;
            if (minc >= 16) keep = 0.50;
            else if (minc >= 12) keep = 0.55;
            else if (minc >= 9) keep = 0.60;
            else if (minc >= 7) keep = 0.65;
            else if (minc >= 5) keep = 0.72;
            else if (minc >= 4) keep = 0.80;
            else if (minc >= 3) keep = 0.87;
            else keep = 0.93;

            int newSize = max(target, (int)floor(sz * keep));
            if (newSize >= sz) break;

            bool improved = false;
            for (int t = 0; t < 25; t++) {
                vector<int> T = sampleSubset(S, newSize);
                int a = ask(T);
                if (a >= 1 && !(a == 1 && newSize > 2 * target)) {
                    S.swap(T);
                    minc = a;
                    improved = true;
                    break;
                }
            }

            if (!improved) {
                int newSize2 = max(target, (newSize + sz) / 2);
                if (newSize2 >= sz) break;
                for (int t = 0; t < 25; t++) {
                    vector<int> T = sampleSubset(S, newSize2);
                    int a = ask(T);
                    if (a >= 1) {
                        S.swap(T);
                        minc = a;
                        improved = true;
                        break;
                    }
                }
                if (!improved) break;
            }
        }

        shrinkToN_Block(S);
        return S;
    }

    void run() {
        cin >> N >> M;
        L = N * M;

        if (M == 1) {
            vector<int> all(L);
            iota(all.begin(), all.end(), 1);
            answer(all);
            return;
        }

        if (N == 1) {
            for (int i = 1; i <= M; i++) answer(vector<int>{i});
            return;
        }

        vector<int> remaining(L);
        iota(remaining.begin(), remaining.end(), 1);

        vector<int> mark(L + 1, 0);
        int tag = 1;

        for (int stickNo = 0; stickNo < M; stickNo++) {
            int mRem = M - stickNo;

            if (mRem == 1) {
                answer(remaining);
                return;
            }

            vector<int> stick = getStick(remaining, mRem);
            answer(stick);

            for (int x : stick) mark[x] = tag;
            vector<int> newRem;
            newRem.reserve(remaining.size() - N);
            for (int x : remaining) if (mark[x] != tag) newRem.push_back(x);
            remaining.swap(newRem);
            ++tag;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver solver;
    solver.run();
    return 0;
}