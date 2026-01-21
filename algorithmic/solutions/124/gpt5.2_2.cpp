#include <bits/stdc++.h>
using namespace std;

static int n;
static long long query_cnt = 0;

static int read_ans() {
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static int ask_pair(int a, int b) {
    ++query_cnt;
    cout << "? 2 " << a << " " << b << "\n";
    cout.flush();
    return read_ans();
}

static int ask_append(const vector<int>& subset, int extra) {
    ++query_cnt;
    cout << "? " << (int)subset.size() + 1;
    for (int x : subset) cout << " " << x;
    cout << " " << extra << "\n";
    cout.flush();
    return read_ans();
}

static int ask_exclude_one(const vector<int>& rem, int excl) {
    ++query_cnt;
    cout << "? " << (int)rem.size() - 1;
    for (int x : rem) if (x != excl) cout << " " << x;
    cout << "\n";
    cout.flush();
    return read_ans();
}

struct DPRes {
    bool ok = false;
    vector<vector<int>> subsetForResidue; // [r] -> indices of size q-1
};

static DPRes build_subsets_for_mod(int q, const vector<int>& knownPos, const vector<int>& perm) {
    DPRes res;
    res.subsetForResidue.assign(q, {});
    int M = (int)knownPos.size();
    if (M < q) return res; // need variety; also implies M < q-1 anyway

    vector<vector<char>> dp(q, vector<char>(q, 0));
    vector<vector<int>> prevMod(q, vector<int>(q, -1));
    vector<vector<int>> prevIdx(q, vector<int>(q, -1));
    dp[0][0] = 1;

    for (int idx = 0; idx < M; idx++) {
        int pos = knownPos[idx];
        int v = perm[pos] % q;
        for (int c = q - 2; c >= 0; c--) {
            for (int m = 0; m < q; m++) if (dp[c][m]) {
                int nm = (m + v) % q;
                if (!dp[c + 1][nm]) {
                    dp[c + 1][nm] = 1;
                    prevMod[c + 1][nm] = m;
                    prevIdx[c + 1][nm] = idx;
                }
            }
        }
    }

    for (int m = 0; m < q; m++) {
        if (!dp[q - 1][m]) return res;
    }

    for (int r = 0; r < q; r++) {
        int targetMod = (q - r) % q;
        vector<int> subset;
        subset.reserve(q - 1);
        int c = q - 1, m = targetMod;
        while (c > 0) {
            int idx = prevIdx[c][m];
            if (idx < 0) break;
            subset.push_back(knownPos[idx]);
            int pm = prevMod[c][m];
            m = pm;
            c--;
        }
        if ((int)subset.size() != q - 1) return res;
        res.subsetForResidue[r] = subset;
    }

    res.ok = true;
    return res;
}

static long long encode_key(const vector<int>& mods, const vector<int>& residues) {
    long long key = 0, mult = 1;
    for (int i = 0; i < (int)mods.size(); i++) {
        key += (long long)residues[i] * mult;
        mult *= mods[i];
    }
    return key;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    if (n == 2) {
        cout << "! 1 2\n";
        cout.flush();
        return 0;
    }

    int maxPairs = min(15, n / 2 - 1);
    if (maxPairs < 1) maxPairs = 1;

    vector<vector<int>> pairs(maxPairs + 1);
    vector<int> remaining;
    remaining.reserve(n);
    for (int i = 1; i <= n; i++) remaining.push_back(i);

    for (int t = 1; t <= maxPairs; t++) {
        vector<int> cand;
        cand.reserve(2);

        for (int pos : remaining) {
            int ans = ask_exclude_one(remaining, pos);
            if (ans == 1) cand.push_back(pos);
        }

        // If this happens, our maxPairs was too big (remaining size 2 -> k=1 makes all answers 1)
        if ((int)cand.size() != 2) {
            // Fallback: stop early
            maxPairs = t - 1;
            pairs.resize(maxPairs + 1);
            break;
        }

        pairs[t] = cand;

        vector<int> newRem;
        newRem.reserve((int)remaining.size() - 2);
        for (int x : remaining) if (x != cand[0] && x != cand[1]) newRem.push_back(x);
        remaining.swap(newRem);
    }

    vector<int> perm(n + 1, 0);
    vector<char> isOdd(n + 1, 0);

    int basePos = pairs[1][0];
    isOdd[basePos] = 1;
    for (int i = 1; i <= n; i++) {
        if (i == basePos) continue;
        int ans = ask_pair(basePos, i);
        isOdd[i] = (ans == 1);
    }

    for (int t = 1; t <= maxPairs; t++) {
        int a = pairs[t][0], b = pairs[t][1];
        if (t % 2 == 1) {
            if (isOdd[a]) { perm[a] = t; perm[b] = n + 1 - t; }
            else          { perm[b] = t; perm[a] = n + 1 - t; }
        } else {
            if (!isOdd[a]) { perm[a] = t; perm[b] = n + 1 - t; }
            else           { perm[b] = t; perm[a] = n + 1 - t; }
        }
    }

    // If only 2 positions remain, they must be values (maxPairs+1) and (n-maxPairs)
    if ((int)remaining.size() == 2) {
        int v1 = maxPairs + 1;
        int v2 = n - maxPairs;
        int p1 = remaining[0], p2 = remaining[1];
        if ((v1 % 2) == 1) {
            if (isOdd[p1]) { perm[p1] = v1; perm[p2] = v2; }
            else           { perm[p2] = v1; perm[p1] = v2; }
        } else {
            if (isOdd[p1]) { perm[p1] = v2; perm[p2] = v1; }
            else           { perm[p2] = v2; perm[p1] = v1; }
        }

        if (perm[1] > n / 2) {
            for (int i = 1; i <= n; i++) perm[i] = n + 1 - perm[i];
        }

        cout << "! ";
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << " ";
            cout << perm[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    // Build mod list
    vector<int> mods;
    for (int p : {2, 3, 5, 7, 11}) if (p <= n) mods.push_back(p);

    long long prod = 1;
    for (int m : mods) prod *= m;
    vector<int> decode(prod, 0);
    for (int v = 1; v <= n; v++) {
        vector<int> residues(mods.size());
        for (int i = 0; i < (int)mods.size(); i++) residues[i] = v % mods[i];
        long long key = encode_key(mods, residues);
        decode[key] = v;
    }

    vector<int> knownPos;
    knownPos.reserve(n);
    for (int i = 1; i <= n; i++) if (perm[i] != 0) knownPos.push_back(i);

    // Precompute subsets for each modulus > 2
    vector<DPRes> subsets(12);
    for (int q : mods) {
        if (q == 2) continue;
        subsets[q] = build_subsets_for_mod(q, knownPos, perm);
        if (!subsets[q].ok) {
            // Extend known pairs until OK (very unlikely needed with maxPairs=15)
            while (!subsets[q].ok && (int)remaining.size() >= 4) {
                int nextT = maxPairs + 1;
                vector<int> cand;
                for (int pos : remaining) {
                    int ans = ask_exclude_one(remaining, pos);
                    if (ans == 1) cand.push_back(pos);
                }
                if ((int)cand.size() != 2) break;

                // assign using parity
                int a = cand[0], b = cand[1];
                if (nextT % 2 == 1) {
                    if (isOdd[a]) { perm[a] = nextT; perm[b] = n + 1 - nextT; }
                    else          { perm[b] = nextT; perm[a] = n + 1 - nextT; }
                } else {
                    if (!isOdd[a]) { perm[a] = nextT; perm[b] = n + 1 - nextT; }
                    else           { perm[b] = nextT; perm[a] = n + 1 - nextT; }
                }

                // update remaining/known
                vector<int> newRem;
                newRem.reserve((int)remaining.size() - 2);
                for (int x : remaining) if (x != a && x != b) newRem.push_back(x);
                remaining.swap(newRem);
                knownPos.push_back(a);
                knownPos.push_back(b);
                maxPairs++;

                subsets[q] = build_subsets_for_mod(q, knownPos, perm);
            }
        }
    }

    // Determine unknown positions via residues
    for (int pos : remaining) {
        vector<int> residues(mods.size(), 0);
        for (int mi = 0; mi < (int)mods.size(); mi++) {
            int q = mods[mi];
            if (q == 2) {
                residues[mi] = isOdd[pos] ? 1 : 0;
                continue;
            }
            int found = -1;
            for (int r = 0; r < q; r++) {
                int ans = ask_append(subsets[q].subsetForResidue[r], pos);
                if (ans == 1) {
                    found = r;
                    break;
                }
            }
            if (found < 0) found = 0;
            residues[mi] = found;
        }

        long long key = encode_key(mods, residues);
        int v = (key >= 0 && key < (long long)decode.size()) ? decode[key] : 0;
        perm[pos] = v;
    }

    // Canonicalize
    if (perm[1] > n / 2) {
        for (int i = 1; i <= n; i++) perm[i] = n + 1 - perm[i];
    }

    cout << "! ";
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << perm[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}