#include <bits/stdc++.h>
using namespace std;

static int N, M;
static int L;
static long long queryCount = 0;
static mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

static int ask(const vector<int>& v) {
    cout << "? " << (int)v.size();
    for (int x : v) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    ++queryCount;
    return ans;
}

static void answerStick(const vector<int>& v) {
    cout << "!";
    for (int x : v) cout << ' ' << x;
    cout << '\n';
    cout.flush();
}

static void reduceToStick(vector<int>& C, int target) {
    // C is known to satisfy f(C) >= 1 (contains all colors at least once).
    // Reduce it to an inclusion-minimal such set; then its size is exactly N.

    int b = 16;
    while ((int)C.size() > target) {
        bool removed_any = false;
        // Try a few random partitions at the same granularity.
        for (int rep = 0; rep < 3 && !removed_any && (int)C.size() > target; rep++) {
            shuffle(C.begin(), C.end(), rng);
            int chunk_size = max(1, (int)C.size() / b);
            if (chunk_size <= 1) break;

            for (int start = 0; start < (int)C.size() && (int)C.size() > target; ) {
                int end = min((int)C.size(), start + chunk_size);

                vector<int> C2;
                C2.reserve(C.size() - (end - start));
                C2.insert(C2.end(), C.begin(), C.begin() + start);
                C2.insert(C2.end(), C.begin() + end, C.end());

                if (ask(C2) >= 1) {
                    C.swap(C2);
                    removed_any = true;
                    // Try removing again starting at same position (new elements shifted into [start, ...)).
                } else {
                    start = end;
                }
            }
        }
        if (!removed_any) {
            b *= 2;
            if (b > (int)C.size()) break;
        }
    }

    // Final single-pass element elimination; each index is tested at most once.
    for (int i = 0; i < (int)C.size() && (int)C.size() > N; ) {
        vector<int> C2;
        C2.reserve(C.size() - 1);
        C2.insert(C2.end(), C.begin(), C.begin() + i);
        C2.insert(C2.end(), C.begin() + i + 1, C.end());

        if (ask(C2) >= 1) {
            C.swap(C2);
        } else {
            i++;
        }
    }

    // Safety: if still larger (shouldn't happen), repeat.
    while ((int)C.size() > N) {
        bool changed = false;
        for (int i = 0; i < (int)C.size() && (int)C.size() > N; ) {
            vector<int> C2;
            C2.reserve(C.size() - 1);
            C2.insert(C2.end(), C.begin(), C.begin() + i);
            C2.insert(C2.end(), C.begin() + i + 1, C.end());
            if (ask(C2) >= 1) {
                C.swap(C2);
                changed = true;
            } else {
                i++;
            }
        }
        if (!changed) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    L = N * M;

    if (N == 1) {
        for (int j = 1; j <= M; j++) answerStick({j});
        return 0;
    }
    if (M == 1) {
        vector<int> v;
        v.reserve(N);
        for (int i = 1; i <= N; i++) v.push_back(i);
        answerStick(v);
        return 0;
    }

    vector<char> used(L + 1, 0);
    vector<int> rem;
    rem.reserve(L);
    for (int i = 1; i <= L; i++) rem.push_back(i);

    for (int stickNo = 0; stickNo < M; stickNo++) {
        if (stickNo == M - 1) {
            // Remaining must be exactly one stick.
            vector<int> last = rem;
            if ((int)last.size() != N) {
                // Fallback: rebuild from used array
                last.clear();
                for (int i = 1; i <= L; i++) if (!used[i]) last.push_back(i);
            }
            answerStick(last);
            return 0;
        }

        vector<int> C = rem;

        // Ensure C contains all colors (it should, by construction); no query needed.

        int add = min(50, N);
        int target = N + add;
        if (target < N) target = N;
        if (target > (int)C.size()) target = max(N, (int)C.size());

        reduceToStick(C, target);

        if ((int)C.size() != N) {
            // As a robust fallback, force down to N with element elimination.
            for (int i = 0; i < (int)C.size() && (int)C.size() > N; ) {
                vector<int> C2;
                C2.reserve(C.size() - 1);
                C2.insert(C2.end(), C.begin(), C.begin() + i);
                C2.insert(C2.end(), C.begin() + i + 1, C.end());
                if (ask(C2) >= 1) C.swap(C2);
                else i++;
            }
        }

        answerStick(C);

        for (int x : C) used[x] = 1;

        vector<int> newrem;
        newrem.reserve(rem.size() - N);
        for (int x : rem) if (!used[x]) newrem.push_back(x);
        rem.swap(newrem);
    }

    return 0;
}