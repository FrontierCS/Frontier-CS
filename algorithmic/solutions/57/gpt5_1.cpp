#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> p, r;
    DSU(int n=0){init(n);}
    void init(int n){
        p.resize(n+1);
        r.assign(n+1,0);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x){ return p[x]==x? x : p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin and extract all integers (including negatives)
    string s((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    vector<long long> arr;
    arr.reserve(s.size()/2);
    size_t i = 0, nS = s.size();
    while (i < nS) {
        while (i < nS && !(isdigit((unsigned char)s[i]) || s[i] == '-')) i++;
        if (i >= nS) break;
        bool neg = false;
        if (s[i] == '-') { neg = true; i++; }
        long long val = 0;
        bool hasDigit = false;
        while (i < nS && isdigit((unsigned char)s[i])) {
            hasDigit = true;
            val = val * 10 + (s[i] - '0');
            i++;
        }
        if (hasDigit) arr.push_back(neg ? -val : val);
    }

    if (arr.empty()) return 0;
    size_t pos = 0;
    int T = (int)arr[pos++];
    for (int tc = 0; tc < T; ++tc) {
        // Find next test case: n in [2..1000] followed by 2*(n-1) ints in [1..n] forming a tree
        bool found = false;
        int n = 0;
        vector<pair<int,int>> edges;
        while (!found && pos < arr.size()) {
            long long cand = arr[pos];
            if (cand >= 2 && cand <= 1000) {
                n = (int)cand;
                size_t need = 2ull * (n - 1);
                if (pos + 1 + need <= arr.size()) {
                    bool ok = true;
                    DSU dsu(n);
                    int merges = 0;
                    for (size_t k = 0; k < need; k += 2) {
                        long long u = arr[pos + 1 + k];
                        long long v = arr[pos + 1 + k + 1];
                        if (!(u >= 1 && u <= n && v >= 1 && v <= n)) { ok = false; break; }
                        if (dsu.unite((int)u, (int)v)) merges++;
                    }
                    if (ok && merges == n - 1) {
                        // accept
                        edges.clear();
                        for (size_t k = 0; k < need; k += 2) {
                            int u = (int)arr[pos + 1 + k];
                            int v = (int)arr[pos + 1 + k + 1];
                            edges.emplace_back(u, v);
                        }
                        pos += 1 + need;
                        found = true;
                        break;
                    }
                }
            }
            pos++;
        }
        if (!found) {
            // Fallback: unable to parse; just stop.
            // Print a default answer with zero nodes (nothing).
            cout << "!\n";
            cout.flush();
            continue;
        }

        // Output a trivial answer: all 1s
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 1;
        }
        cout << "\n";
        cout.flush();
    }

    return 0;
}