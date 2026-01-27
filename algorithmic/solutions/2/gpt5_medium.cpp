#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<vector<long long>> lines;
    string s;
    while (true) {
        string line;
        if (!getline(cin, line)) break;
        // trim
        bool allspace = true;
        for (char c : line) if (!isspace((unsigned char)c)) { allspace = false; break; }
        if (allspace) continue;
        istringstream iss(line);
        vector<long long> v;
        long long x;
        while (iss >> x) v.push_back(x);
        if (!v.empty()) lines.push_back(v);
    }
    if (lines.empty()) return 0;

    auto is_perm = [&](const vector<long long>& v, int n)->bool{
        if ((int)v.size() != n) return false;
        vector<int> seen(n+1, 0);
        for (auto a : v) {
            if (a < 1 || a > n) return false;
            if (seen[(int)a]) return false;
            seen[(int)a] = 1;
        }
        return true;
    };

    int n = -1;
    // Determine n
    if (!lines.empty()) {
        if (lines[0][0] == 0 || lines[0][0] == 1) {
            n = (int)lines[0].size() - 1;
        } else {
            n = (int)lines[0][0];
        }
    }
    if (n <= 0) {
        // Fallback: try infer from a "1 ..." line or a line that looks like a permutation
        for (auto &ln : lines) {
            if (!ln.empty() && ln[0] == 1) {
                n = (int)ln.size() - 1;
                break;
            }
        }
        if (n <= 0) {
            for (auto &ln : lines) {
                // try any line as candidate permutation
                int cand_n = (int)ln.size();
                bool ok = true;
                vector<int> seen(cand_n + 1, 0);
                for (auto a : ln) {
                    if (a < 1 || a > cand_n) { ok = false; break; }
                    if (seen[(int)a]) { ok = false; break; }
                    seen[(int)a] = 1;
                }
                if (ok) { n = cand_n; break; }
            }
        }
    }
    if (n <= 0) return 0;

    vector<long long> perm;
    bool have_perm = false;

    // Prefer line starting with 1 and length n+1
    for (auto &ln : lines) {
        if (!ln.empty() && ln[0] == 1 && (int)ln.size() == n + 1) {
            perm.assign(ln.begin() + 1, ln.end());
            have_perm = true;
        }
    }

    // If not found, check if first line is "n p1..pn"
    if (!have_perm) {
        if (!lines.empty() && !(lines[0][0] == 0 || lines[0][0] == 1) && (int)lines[0].size() >= n + 1) {
            vector<long long> cand(lines[0].begin() + 1, lines[0].begin() + 1 + n);
            if (is_perm(cand, n)) {
                perm = cand; have_perm = true;
            }
        }
    }

    // If still not found, check if second line is the permutation
    if (!have_perm) {
        if ((int)lines.size() >= 2 && !(lines[0][0] == 0 || lines[0][0] == 1)) {
            if (is_perm(lines[1], n)) {
                perm = lines[1]; have_perm = true;
            }
        }
    }

    // Try last line that is a pure permutation
    if (!have_perm) {
        for (int i = (int)lines.size() - 1; i >= 0; --i) {
            if (!lines[i].empty() && !(lines[i][0] == 0 || lines[i][0] == 1)) {
                if (is_perm(lines[i], n)) {
                    perm = lines[i]; have_perm = true;
                    break;
                }
            }
        }
    }

    // Check if there are query lines (starting with 0)
    bool has_query_lines = false;
    for (auto &ln : lines) {
        if (!ln.empty() && ln[0] == 0) { has_query_lines = true; break; }
    }

    if (has_query_lines && have_perm) {
        // Simulate interactor: for each 0-line, output number of matches
        for (auto &ln : lines) {
            if (!ln.empty() && ln[0] == 0) {
                vector<long long> q;
                if ((int)ln.size() >= n + 1) q.assign(ln.begin() + 1, ln.begin() + 1 + n);
                else {
                    // if malformed, pad or skip
                    q.assign(n, 0);
                    for (size_t i = 1; i < ln.size() && i <= (size_t)n; ++i) q[i-1] = ln[i];
                }
                int matches = 0;
                for (int i = 0; i < n; ++i) if (i < (int)q.size() && q[i] == perm[i]) ++matches;
                cout << matches << "\n";
            }
        }
        return 0;
    }

    // Otherwise, if we have a permutation to output, print it
    if (have_perm) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
        return 0;
    }

    // Fallback: if no queries and no permutation found, try output nothing.
    return 0;
}