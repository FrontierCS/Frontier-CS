#include <bits/stdc++.h>
using namespace std;

struct Segment {
    int a;
    int k;
    vector<int> bits;
    int preNode;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long L, R;
    if (!(cin >> L >> R)) return 0;
    
    // Step 1: Decompose [L, R] into dyadic intervals [a*2^k, (a+1)*2^k - 1]
    vector<Segment> segs;
    long long cur = L;
    while (cur <= R) {
        int k = __builtin_ctzll(cur);
        while (cur + (1LL << k) - 1 > R) --k;
        Segment s;
        s.a = int(cur >> k);
        s.k = k;
        segs.push_back(s);
        cur += (1LL << k);
    }
    
    // Step 2: Build trie of proper prefixes of all a's (binary, MSB to LSB)
    struct TrieNode {
        int child[2];
        TrieNode() { child[0] = child[1] = 0; }
    };
    
    vector<TrieNode> trie(2); // index 0 unused, 1 = root (start)
    int root = 1;
    int nextNode = 1; // last used index in trie
    
    int Kmax = 0;
    
    for (auto &seg : segs) {
        int a = seg.a;
        // get bits of a, MSB -> LSB
        string tmp;
        while (a > 0) {
            tmp.push_back(char('0' + (a & 1)));
            a >>= 1;
        }
        reverse(tmp.begin(), tmp.end());
        seg.bits.clear();
        for (char c : tmp) seg.bits.push_back(c - '0');
        int len = (int)seg.bits.size();
        
        int curNode = root;
        if (len > 1) {
            for (int i = 0; i < len - 1; ++i) {
                int b = seg.bits[i];
                if (trie[curNode].child[b] == 0) {
                    trie.push_back(TrieNode());
                    trie[curNode].child[b] = ++nextNode;
                }
                curNode = trie[curNode].child[b];
            }
        }
        // preNode is node corresponding to prefix of length len-1 (or root if len==1)
        seg.preNode = (len == 1) ? root : curNode;
        Kmax = max(Kmax, seg.k);
    }
    
    int prefixN = nextNode; // nodes 1..prefixN are prefix-trie nodes
    // Step 3: Create suffix chain nodes Suf[0..Kmax], Suf[0] is F (end)
    int totalNodes = prefixN + (Kmax + 1);
    vector<int> sufId(Kmax + 1);
    for (int d = 0; d <= Kmax; ++d) {
        sufId[d] = prefixN + 1 + d;
    }
    int F = sufId[0];
    
    // Step 4: Build adjacency lists
    vector<vector<pair<int,int>>> g(totalNodes + 1); // (to, bit)
    
    // Prefix edges from trie
    for (int i = 1; i <= prefixN; ++i) {
        for (int b = 0; b <= 1; ++b) {
            int ch = trie[i].child[b];
            if (ch != 0) {
                g[i].push_back({ch, b});
            }
        }
    }
    
    // Suffix chain edges
    for (int d = 1; d <= Kmax; ++d) {
        int u = sufId[d];
        int v = sufId[d - 1];
        g[u].push_back({v, 0});
        g[u].push_back({v, 1});
    }
    
    // Segment-specific final edges
    for (auto &seg : segs) {
        int len = (int)seg.bits.size();
        int lastBit = seg.bits[len - 1];
        int pre = seg.preNode;
        int dest = (seg.k == 0) ? F : sufId[seg.k];
        g[pre].push_back({dest, lastBit});
    }
    
    // Step 5: Deduplicate edges with same (to, bit) from each node
    for (int u = 1; u <= totalNodes; ++u) {
        auto &vec = g[u];
        sort(vec.begin(), vec.end(), [](const pair<int,int>&x, const pair<int,int>&y){
            if (x.second != y.second) return x.second < y.second;
            return x.first < y.first;
        });
        vec.erase(unique(vec.begin(), vec.end(), [](const pair<int,int>&x, const pair<int,int>&y){
            return x.first == y.first && x.second == y.second;
        }), vec.end());
    }
    
    // Output
    cout << totalNodes << '\n';
    for (int i = 1; i <= totalNodes; ++i) {
        auto &vec = g[i];
        cout << (int)vec.size();
        for (auto &e : vec) {
            cout << ' ' << e.first << ' ' << e.second;
        }
        cout << '\n';
    }
    
    return 0;
}