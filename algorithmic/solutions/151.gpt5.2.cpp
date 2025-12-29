#include <bits/stdc++.h>
using namespace std;

static inline char revDir(char c){
    if(c=='U') return 'D';
    if(c=='D') return 'U';
    if(c=='L') return 'R';
    return 'L'; // 'R'
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> g(N);
    for(int i=0;i<N;i++) cin >> g[i];

    auto inside = [&](int i, int j){ return (0 <= i && i < N && 0 <= j && j < N); };
    auto isRoad = [&](int i, int j){ return inside(i,j) && g[i][j] != '#'; };

    int start = si * N + sj;

    int roads = 0;
    for(int i=0;i<N;i++) for(int j=0;j<N;j++) if(g[i][j] != '#') roads++;

    vector<char> parentDir(N*N, 0);
    vector<unsigned char> vis(N*N, 0);

    struct Frame { int v; int it; };
    vector<Frame> st;
    st.reserve(N*N);

    string ans;
    ans.reserve(max(1, 2 * roads + 10));

    vis[start] = 1;
    st.push_back({start, 0});

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U','D','L','R'};

    while(!st.empty()){
        Frame &f = st.back();
        if(f.it == 4){
            int v = f.v;
            st.pop_back();
            if(!st.empty()){
                ans.push_back(revDir(parentDir[v]));
            }
            continue;
        }
        int v = f.v;
        int i = v / N, j = v % N;

        int k = f.it++;
        int ni = i + di[k], nj = j + dj[k];
        if(!isRoad(ni, nj)) continue;

        int u = ni * N + nj;
        if(vis[u]) continue;

        vis[u] = 1;
        parentDir[u] = dc[k];
        ans.push_back(dc[k]);
        st.push_back({u, 0});
    }

    cout << ans << "\n";
    return 0;
}