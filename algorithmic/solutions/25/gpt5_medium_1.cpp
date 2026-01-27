#include <bits/stdc++.h>
using namespace std;

static bool is01(char c){ return c=='0' || c=='1'; }

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    for(int tc = 0; tc < T; ++tc){
        int n;
        if(!(cin >> n)) return 0;
        string line;
        getline(cin, line); // consume endline after n
        
        vector<vector<int>> adj(n);
        
        // Read next non-empty line
        string first;
        while (true) {
            if(!getline(cin, first)) first = "";
            // Break even if empty; we'll detect formats accordingly.
            // But prefer skipping pure empty lines
            if(!first.empty()) break;
            // if EOF occurred, break and handle
            if(cin.fail()) break;
        }
        if(first.empty()){
            // No further input; assume no edges
            // adj already empty
        } else {
            // Determine format
            // Count number of 0/1 characters in the line
            int bitcnt = 0;
            for(char c: first) if(is01(c)) bitcnt++;
            bool looksMatrixRow = (bitcnt >= n);
            
            if(looksMatrixRow){
                // Adjacency matrix: read n rows including 'first'
                vector<string> rows;
                rows.push_back(first);
                while((int)rows.size() < n){
                    string r;
                    if(!getline(cin, r)) r = "";
                    rows.push_back(r);
                }
                // Parse rows
                for(int i=0;i<n;i++){
                    int collected = 0;
                    for(char c: rows[i]){
                        if(is01(c)){
                            if(collected < n){
                                if(c=='1' && collected!=i){
                                    adj[i].push_back(collected);
                                }
                                collected++;
                            }
                        }
                    }
                    // If fewer than n bits found, try to parse tokens separated by spaces
                    if(collected < n){
                        // Try token-based parsing
                        stringstream ss(rows[i]);
                        vector<int> bits;
                        string tok;
                        while(ss >> tok){
                            if(tok=="0" || tok=="1") bits.push_back(tok[0]-'0');
                        }
                        for(int j=0;j<min(n,(int)bits.size());++j){
                            if(bits[j]==1 && j!=i) adj[i].push_back(j);
                        }
                    }
                }
            } else {
                // Edge list: first line starts with m (possibly followed by some numbers)
                // Parse ints from 'first'
                stringstream ss(first);
                long long mll;
                if(!(ss >> mll)) mll = 0;
                long long m = max(0LL, mll);
                vector<int> nums;
                int x;
                while(ss >> x) nums.push_back(x);
                // Keep reading until we have 2*m integers
                while((long long)nums.size() < 2*m){
                    string r;
                    if(!getline(cin, r)) break;
                    stringstream s2(r);
                    int y;
                    while(s2 >> y) nums.push_back(y);
                }
                for(long long i=0;i<m;i++){
                    int u = nums[2*i];
                    int v = nums[2*i+1];
                    if(1 <= u && u <= n && 1 <= v && v <= n && u != v){
                        adj[u-1].push_back(v-1);
                        adj[v-1].push_back(u-1);
                    }
                }
            }
        }
        
        // Determine connectivity
        vector<int> vis(n,0);
        queue<int> q;
        if(n>0){
            vis[0]=1; q.push(0);
            while(!q.empty()){
                int u=q.front(); q.pop();
                for(int v: adj[u]){
                    if(!vis[v]){
                        vis[v]=1; q.push(v);
                    }
                }
            }
        }
        bool connected = true;
        for(int i=0;i<n;i++) if(!vis[i]) { connected=false; break; }
        
        cout << "! " << (connected ? 1 : 0) << "\n";
        cout.flush();
    }
    return 0;
}