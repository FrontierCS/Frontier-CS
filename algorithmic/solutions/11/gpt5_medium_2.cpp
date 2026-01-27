#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<string> g(n);
    for (int i = 0; i < n; ++i) cin >> g[i];
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    auto inb = [&](int r, int c){ return r>=0 && r<n && c>=0 && c<m; };
    // Count blanks and check connectivity
    int totalBlank = 0;
    for(int i=0;i<n;++i) for(int j=0;j<m;++j) if(g[i][j]=='1') ++totalBlank;
    if (g[sr][sc] != '1' || g[er][ec] != '1') {
        cout << -1 << '\n';
        return 0;
    }
    // BFS from start
    vector<vector<int>> vis(n, vector<int>(m, 0));
    queue<pair<int,int>> q;
    vis[sr][sc]=1;
    q.push({sr,sc});
    int reach=0;
    while(!q.empty()){
        auto [r,c]=q.front(); q.pop();
        ++reach;
        const int dr[4]={0,0,-1,1};
        const int dc[4]={-1,1,0,0};
        for(int k=0;k<4;++k){
            int nr=r+dr[k], nc=c+dc[k];
            if(inb(nr,nc) && !vis[nr][nc] && g[nr][nc]=='1'){
                vis[nr][nc]=1;
                q.push({nr,nc});
            }
        }
    }
    if (reach != totalBlank) {
        cout << -1 << '\n';
        return 0;
    }
    if (totalBlank == 1) {
        // Only one blank, and sr==er necessarily
        cout << '\n';
        return 0;
    }

    // Build base sequences B, then W = B + reverse(B) palindromic blocks
    vector<string> Bs;

    auto repeatChar = [&](char c, int t){
        if (t<=0) return string();
        return string(t, c);
    };

    // Horizontal snake downwards
    {
        string b;
        for(int i=0;i<n;i++){
            if (i%2==0) b += repeatChar('R', m-1);
            else b += repeatChar('L', m-1);
            if (i != n-1) b += 'D';
        }
        Bs.push_back(b);
    }
    // Horizontal snake upwards
    {
        string b;
        for(int i=0;i<n;i++){
            if (i%2==0) b += repeatChar('L', m-1);
            else b += repeatChar('R', m-1);
            if (i != n-1) b += 'U';
        }
        Bs.push_back(b);
    }
    // Vertical snake rightwards
    {
        string b;
        for(int j=0;j<m;j++){
            if (j%2==0) b += repeatChar('D', n-1);
            else b += repeatChar('U', n-1);
            if (j != m-1) b += 'R';
        }
        Bs.push_back(b);
    }
    // Vertical snake leftwards
    {
        string b;
        for(int j=0;j<m;j++){
            if (j%2==0) b += repeatChar('U', n-1);
            else b += repeatChar('D', n-1);
            if (j != m-1) b += 'L';
        }
        Bs.push_back(b);
    }
    // Combined snakes
    {
        string b;
        // H down
        for(int i=0;i<n;i++){
            if (i%2==0) b += repeatChar('R', m-1);
            else b += repeatChar('L', m-1);
            if (i != n-1) b += 'D';
        }
        // V right
        for(int j=0;j<m;j++){
            if (j%2==0) b += repeatChar('D', n-1);
            else b += repeatChar('U', n-1);
            if (j != m-1) b += 'R';
        }
        // H up
        for(int i=0;i<n;i++){
            if (i%2==0) b += repeatChar('L', m-1);
            else b += repeatChar('R', m-1);
            if (i != n-1) b += 'U';
        }
        // V left
        for(int j=0;j<m;j++){
            if (j%2==0) b += repeatChar('U', n-1);
            else b += repeatChar('D', n-1);
            if (j != m-1) b += 'L';
        }
        Bs.push_back(b);
    }
    // Mix of simple cycles repeated
    auto addMix = [&](string pat, int times){
        string b;
        b.reserve(pat.size()*times);
        for(int i=0;i<times;i++) b += pat;
        Bs.push_back(b);
    };
    int mixTimes = max(2, (n*m)/2);
    addMix("URDL", mixTimes);
    addMix("RDLU", mixTimes);
    addMix("DLUR", mixTimes);
    addMix("LURD", mixTimes);

    // Build palindromic blocks W = B + reverse(B)
    vector<string> Ws;
    for (auto &B : Bs) {
        string R = B;
        reverse(R.begin(), R.end());
        string W = B + R;
        if (!W.empty()) Ws.push_back(W);
    }
    // Add a shorter palindrome block as fallback
    Ws.push_back(string("UDLRRLLRDLU") + string("ULDRLLRRDLU")); // arbitrary-ish; will be pal after making reverse
    // Actually ensure pal:
    {
        string B = "UDLRRLLRDLU";
        string R = B; reverse(R.begin(), R.end());
        Ws.back() = B + R;
    }

    // Directions mapping
    auto step = [&](int r, int c, char mv, int &nr, int &nc){
        nr = r; nc = c;
        if (mv == 'L') nc = c - 1;
        else if (mv == 'R') nc = c + 1;
        else if (mv == 'U') nr = r - 1;
        else if (mv == 'D') nr = r + 1;
        if (!(inb(nr,nc) && g[nr][nc]=='1')) {
            nr = r; nc = c;
        }
    };

    // Try each W and K
    for (auto &W : Ws) {
        int L = (int)W.size();
        if (L == 0) continue;
        int maxK_by_len = (int)(1000000LL / L);
        int Kmax = min(2000, maxK_by_len);
        if (Kmax <= 0) continue;

        vector<char> visited(n*m, 0);
        int r = sr, c = sc;
        visited[r*m + c] = 1;
        int visCnt = 1;

        // For efficiency, precompute positions after applying W once from any cell? Too heavy; do stepwise.
        // We'll simulate cumulatively for k=1..Kmax
        for (int k = 1; k <= Kmax; ++k) {
            for (int i = 0; i < L; ++i) {
                int nr, nc;
                step(r, c, W[i], nr, nc);
                r = nr; c = nc;
                int idx = r*m + c;
                if (!visited[idx]) {
                    visited[idx] = 1;
                    ++visCnt;
                }
            }
            if (visCnt == totalBlank && r == er && c == ec) {
                // Construct output S = W repeated k times
                string out;
                out.reserve((size_t)L * k);
                for (int t=0;t<k;++t) out += W;
                cout << out << '\n';
                return 0;
            }
        }
    }

    cout << -1 << '\n';
    return 0;
}