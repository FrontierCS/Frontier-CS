#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    // Choose moduli such that sum of moduli <= R and product large
    vector<int> mods = {3, 13, 17, 19, 23}; // sum = 75
    int sum_mods = 0;
    for (int p : mods) sum_mods += p;
    while (sum_mods > R && !mods.empty()) {
        sum_mods -= mods.back();
        mods.pop_back();
    }

    int robots_sent = 0;
    // Send queries: for each modulus p, for each residue r, query all positions i in [1..1000] where i % p == r
    for (int p : mods) {
        for (int r = 0; r < p; ++r) {
            vector<int> lst;
            lst.reserve(1000 / p + 2);
            for (int i = 1; i <= 1000; ++i) {
                if (i % p == r) lst.push_back(i);
            }
            cout << "? " << lst.size();
            for (int x : lst) cout << " " << x;
            cout << "\n";
            cout.flush();
            robots_sent++;
        }
    }

    // Get all answers
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    // Decode residue sets per modulus
    vector<vector<int>> residue_sets; // for each modulus, list of residues with answer 1
    residue_sets.reserve(mods.size());
    int offset = 0;
    for (int p : mods) {
        vector<int> rs;
        for (int r = 0; r < p; ++r) {
            if (offset + r < (int)ans.size() && ans[offset + r] == 1) {
                rs.push_back(r);
            }
        }
        residue_sets.push_back(rs);
        offset += p;
    }

    // Precompute allowed residues per modulus for quick checking
    vector<vector<char>> allowed;
    allowed.reserve(mods.size());
    for (size_t t = 0; t < mods.size(); ++t) {
        int p = mods[t];
        vector<char> ok(p, 0);
        for (int r : residue_sets[t]) ok[r] = 1;
        allowed.push_back(move(ok));
    }

    // Candidates: numbers 1..1000 whose residues are in the allowed set for all moduli
    vector<int> candidates;
    for (int i = 1; i <= 1000; ++i) {
        bool ok = true;
        for (size_t t = 0; t < mods.size(); ++t) {
            int p = mods[t];
            int r = i % p;
            if (r < 0) r += p;
            if (!allowed[t][r]) { ok = false; break; }
        }
        if (ok) candidates.push_back(i);
    }

    auto matches_all = [&](int x, int y) -> bool {
        for (size_t t = 0; t < mods.size(); ++t) {
            int p = mods[t];
            int rx = x % p; if (rx < 0) rx += p;
            int ry = y % p; if (ry < 0) ry += p;
            const auto &rs = residue_sets[t];
            if (rs.size() == 0) return false; // shouldn't happen
            if (rs.size() == 1) {
                if (!(rx == rs[0] && ry == rs[0])) return false;
            } else if (rs.size() == 2) {
                if (!((rx == rs[0] && ry == rs[1]) || (rx == rs[1] && ry == rs[0]))) return false;
            } else {
                // More than 2 residues detected is impossible with 2 chairmen and OR queries
                return false;
            }
        }
        return true;
    };

    int a = 1, b = 1;
    bool found = false;

    if (candidates.size() == 1) {
        a = b = candidates[0];
        found = true;
    } else if (candidates.size() >= 2) {
        for (size_t i = 0; i < candidates.size() && !found; ++i) {
            for (size_t j = i; j < candidates.size() && !found; ++j) {
                int x = candidates[i], y = candidates[j];
                if (matches_all(x, y)) {
                    a = x; b = y;
                    found = true;
                }
            }
        }
        if (!found) {
            // Fallback: choose first two candidates
            a = candidates[0];
            b = candidates.size() > 1 ? candidates[1] : candidates[0];
            found = true;
        }
    } else {
        // No candidates found due to unexpected issue; fallback
        a = b = 1;
    }

    cout << "! " << a << " " << b << "\n";
    cout.flush();

    return 0;
}