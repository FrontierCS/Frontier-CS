#include <bits/stdc++.h>
using namespace std;

static inline void appendInt(string &s, int x) {
    char buf[16];
    auto res = to_chars(buf, buf + 16, x);
    s.append(buf, res.ptr);
}

struct Interactor {
    string out;

    Interactor() { out.reserve(8192); }

    int query_except(const vector<int> &rem, int skipPos) {
        int k = (int)rem.size() - 1;
        out.clear();
        out += "? ";
        appendInt(out, k);
        for (int i = 0; i < (int)rem.size(); i++) {
            if (i == skipPos) continue;
            out.push_back(' ');
            appendInt(out, rem[i]);
        }
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);

        int ans;
        if (scanf("%d", &ans) != 1) exit(0);
        if (ans == -1) exit(0);
        return ans;
    }

    int query_two(int a, int b) {
        out.clear();
        out += "? 2 ";
        appendInt(out, a);
        out.push_back(' ');
        appendInt(out, b);
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);

        int ans;
        if (scanf("%d", &ans) != 1) exit(0);
        if (ans == -1) exit(0);
        return ans;
    }

    void answer(const vector<int> &p) {
        out.clear();
        out += "! ";
        for (int i = 1; i < (int)p.size(); i++) {
            if (i > 1) out.push_back(' ');
            appendInt(out, p[i]);
        }
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);
        exit(0);
    }
};

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;

    Interactor it;

    int half = n / 2;
    vector<pair<int,int>> pairPos(half + 1, {-1, -1});

    vector<int> rem(n);
    iota(rem.begin(), rem.end(), 1);

    // Randomize order to reduce expected number of queries per step.
    {
        std::mt19937 rng(712367821);
        shuffle(rem.begin(), rem.end(), rng);
    }

    // Find unordered pairs {d, n-d+1} for d=1..half-1
    for (int d = 1; d <= half - 1; d++) {
        int m = (int)rem.size(); // m >= 4
        int foundA = -1, foundB = -1;
        int posA = -1, posB = -1;

        for (int i = 0; i < m && foundB == -1; i++) {
            int ans = it.query_except(rem, i);
            if (ans == 1) {
                if (foundA == -1) {
                    foundA = rem[i];
                    posA = i;
                } else {
                    foundB = rem[i];
                    posB = i;
                }
            }
        }

        if (foundA == -1 || foundB == -1) return 0;

        pairPos[d] = {foundA, foundB};

        // Remove the two indices from rem using swap-pop, remove larger position first.
        if (posA > posB) {
            swap(posA, posB);
            swap(foundA, foundB);
        }
        // posB > posA
        swap(rem[posB], rem.back());
        rem.pop_back();
        swap(rem[posA], rem.back());
        rem.pop_back();
    }

    // Remaining two indices correspond to last pair {half, half+1}
    int lastU = rem[0], lastV = rem[1];

    vector<int> p(n + 1, 0);

    // Determine which pair contains position 1, and use p1 <= n/2 to orient that pair.
    int d0 = -1;
    int other = -1;
    for (int d = 1; d <= half - 1; d++) {
        auto [u, v] = pairPos[d];
        if (u == 1 || v == 1) {
            d0 = d;
            other = (u == 1 ? v : u);
            break;
        }
    }
    if (d0 == -1) {
        d0 = half;
        other = (lastU == 1 ? lastV : lastU);
        p[1] = half;
        p[other] = half + 1;
    } else {
        p[1] = d0;
        p[other] = n - d0 + 1;
    }

    // Determine absolute parity of all positions using position 1 as reference.
    vector<char> isOdd(n + 1, 0);
    isOdd[1] = (p[1] & 1) ? 1 : 0;
    for (int i = 2; i <= n; i++) {
        int ans = it.query_two(1, i); // 1 if same parity
        isOdd[i] = (ans ? isOdd[1] : (char)(!isOdd[1]));
    }

    // Orient all found pairs using parity.
    for (int d = 1; d <= half - 1; d++) {
        auto [u, v] = pairPos[d];
        char oddSmall = (d & 1) ? 1 : 0;
        if (isOdd[u] == oddSmall) {
            p[u] = d;
            p[v] = n - d + 1;
        } else {
            p[u] = n - d + 1;
            p[v] = d;
        }
    }

    // Orient last pair {half, half+1}
    {
        int d = half;
        char oddSmall = (d & 1) ? 1 : 0;
        int u = lastU, v = lastV;
        if (isOdd[u] == oddSmall) {
            p[u] = d;
            p[v] = d + 1;
        } else {
            p[u] = d + 1;
            p[v] = d;
        }
    }

    // Ensure orientation requirement (should already hold)
    if (p[1] > half) {
        for (int i = 1; i <= n; i++) p[i] = n + 1 - p[i];
    }

    it.answer(p);
    return 0;
}