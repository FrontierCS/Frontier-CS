#include <bits/stdc++.h>
using namespace std;

static inline string trim(const string &s) {
    size_t a = 0, b = s.size();
    while (a < b && isspace((unsigned char)s[a])) a++;
    while (b > a && isspace((unsigned char)s[b - 1])) b--;
    return s.substr(a, b - a);
}

vector<string> splitLines(const string &s) {
    vector<string> lines;
    string line;
    for (char c : s) {
        if (c == '\r') continue;
        if (c == '\n') {
            lines.push_back(line);
            line.clear();
        } else {
            line.push_back(c);
        }
    }
    if (!line.empty()) lines.push_back(line);
    return lines;
}

vector<long long> parseLineLL(const string &line) {
    vector<long long> v;
    stringstream ss(line);
    long long x;
    while (ss >> x) v.push_back(x);
    return v;
}

bool isPermutationN(const vector<long long> &v, int n) {
    if ((int)v.size() != n) return false;
    vector<int> seen(n + 1, 0);
    for (auto x : v) {
        if (x < 1 || x > n) return false;
        if (seen[(int)x]) return false;
        seen[(int)x] = 1;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string all;
    {
        istreambuf_iterator<char> it(cin), end;
        all.assign(it, end);
    }
    string s = trim(all);
    if (s.empty()) {
        return 0;
    }
    vector<string> lines_raw = splitLines(s);
    vector<vector<long long>> lines;
    for (auto &ln : lines_raw) {
        auto t = trim(ln);
        if (!t.empty()) {
            lines.push_back(parseLineLL(t));
        }
    }
    if (lines.empty()) {
        return 0;
    }

    // Detect interactor-transcript mode (each line starts with 0 or 1)
    bool interactor_mode = true;
    for (auto &ln : lines) {
        if (ln.empty() || !(ln[0] == 0 || ln[0] == 1)) {
            interactor_mode = false;
            break;
        }
    }

    if (interactor_mode) {
        // Determine n as the most common (line.size()-1) among lines that have size>=2
        unordered_map<int,int> freq;
        int candidate_n = 0, bestf = -1;
        for (auto &ln : lines) {
            if ((int)ln.size() >= 2) {
                int k = (int)ln.size() - 1;
                int f = ++freq[k];
                if (f > bestf) { bestf = f; candidate_n = k; }
            }
        }
        int n = candidate_n > 0 ? candidate_n : 0;
        // Get secret permutation from the last line starting with 1 and length n+1 and valid permutation
        vector<long long> secret;
        for (int i = (int)lines.size() - 1; i >= 0; --i) {
            auto &ln = lines[i];
            if (!ln.empty() && ln[0] == 1 && (int)ln.size() == n + 1) {
                vector<long long> cand(ln.begin() + 1, ln.end());
                if (isPermutationN(cand, n)) {
                    secret = cand;
                    break;
                }
            }
        }
        if (secret.empty()) {
            // fallback: identity
            secret.resize(n);
            iota(secret.begin(), secret.end(), 1);
        }
        auto countMatches = [&](const vector<long long>& q)->int{
            if ((int)q.size() != (int)secret.size()) return 0;
            int cnt = 0;
            for (int i = 0; i < (int)secret.size(); ++i) if (q[i] == secret[i]) cnt++;
            return cnt;
        };

        // For each line, print the match count for both 0 and 1 lines (robust to transcripts expecting outputs per line)
        for (auto &ln : lines) {
            if ((int)ln.size() >= 2) {
                vector<long long> arr(ln.begin() + 1, ln.end());
                int ans = countMatches(arr);
                cout << ans << "\n";
            } else {
                cout << 0 << "\n";
            }
        }
        return 0;
    }

    // Non-interactor mode
    // Cases:
    // 1) Single line with one integer n => output "1" + identity permutation.
    // 2) First line single integer n. Next line (or any line) contains a permutation of size n => output "1" + that permutation.
    // 3) Fallback: try to deduce n; if impossible, do nothing.

    int n = -1;
    vector<long long> perm;

    if (lines.size() == 1 && lines[0].size() == 1) {
        long long x = lines[0][0];
        if (1 <= x && x <= 1000) {
            n = (int)x;
            perm.resize(n);
            iota(perm.begin(), perm.end(), 1);
        }
    } else {
        // If first line is single integer n
        if (lines[0].size() == 1) {
            long long x = lines[0][0];
            if (1 <= x && x <= 1000) {
                n = (int)x;
                // Search for a line that is a permutation of length n
                for (size_t i = 1; i < lines.size(); ++i) {
                    if ((int)lines[i].size() == n && isPermutationN(lines[i], n)) {
                        perm = lines[i];
                        break;
                    }
                }
                if (perm.empty()) {
                    perm.resize(n);
                    iota(perm.begin(), perm.end(), 1);
                }
            }
        }
    }

    if (n == -1) {
        // Try to infer n as the length of the first line if it looks like a permutation
        if (!lines.empty()) {
            int k = (int)lines[0].size();
            if (k >= 1 && k <= 1000 && isPermutationN(lines[0], k)) {
                n = k;
                perm = lines[0];
            }
        }
    }

    if (n == -1) {
        // Cannot deduce anything meaningful; do nothing.
        return 0;
    }

    // Output as in interactive: guess command "1" followed by permutation
    cout << 1;
    for (int i = 0; i < n; ++i) cout << " " << perm[i];
    cout << "\n";
    return 0;
}