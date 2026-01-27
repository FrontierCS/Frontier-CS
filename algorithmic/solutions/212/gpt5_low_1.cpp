#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s;
    if(!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    // Basic validations
    if (Sy != L) {
        cout << "NO\n";
        return 0;
    }
    vector<int> seenRow(n+1,0);
    for (int x: q) {
        if (x < 1 || x > n || seenRow[x]) {
            cout << "NO\n";
            return 0;
        }
        seenRow[x]=1;
    }

    auto buildOrder = [&](int dir)->vector<int>{
        vector<int> order;
        order.push_back(Sx);
        if (dir==+1) {
            for (int i=Sx+1;i<=n;i++) order.push_back(i);
            for (int i=Sx-1;i>=1;i--) order.push_back(i);
        } else {
            for (int i=Sx-1;i>=1;i--) order.push_back(i);
            for (int i=Sx+1;i<=n;i++) order.push_back(i);
        }
        return order;
    };
    auto isSubseq = [&](const vector<int>& order)->bool{
        int j=0;
        for (int v: order) {
            if (j<Lq && v==q[j]) j++;
        }
        return j==Lq;
    };
    auto endSideAtEdge = [&](int dir)->int{ // 0 for L, 1 for R
        int E1 = (dir==+1)? n : 1;
        int diff = abs(E1 - Sx);
        // Start row ends at R. End side flips each row.
        return (diff % 2 == 0) ? 1 : 0; // 1 -> R, 0 -> L
    };
    auto sideAvailable = [&](int side)->bool{
        if (side==1) return R < m; // R side needs R+1
        else return L > 1; // L side needs L-1
    };

    bool hasOutside = (L>1) || (R<m);
    int chosenDir = 0;
    if (L==1 && R==m) {
        if (Sx!=1 && Sx!=n) {
            cout << "NO\n";
            return 0;
        }
        chosenDir = (Sx==1)? +1 : -1;
        auto ord = buildOrder(chosenDir);
        if (!isSubseq(ord)) {
            cout << "NO\n";
            return 0;
        }
    } else {
        // Try both directions, must end at edge side that has outside column and subseq satisfied
        for (int dirTry : {+1,-1}) {
            int side = endSideAtEdge(dirTry);
            if (!sideAvailable(side)) continue;
            auto ord = buildOrder(dirTry);
            if (!isSubseq(ord)) continue;
            chosenDir = dirTry;
            break;
        }
        if (chosenDir==0) {
            cout << "NO\n";
            return 0;
        }
    }

    // Build path
    vector<pair<int,int>> path;
    vector<vector<char>> vis(n+1, vector<char>(m+1, 0));
    auto append = [&](int x,int y){
        if (x<1||x>n||y<1||y>m) {
            // Should not happen in valid construction
        }
        if (vis[x][y]) {
            // Should not happen
        }
        vis[x][y]=1;
        path.emplace_back(x,y);
    };
    auto moveLine = [&](int x,int y){
        // move in straight line from current to (x,y)
        auto [cx,cy] = path.back();
        if (cx==x) {
            int sy = (cy<y)? 1 : -1;
            for (int j=cy+sy; j!=y+sy; j+=sy) append(cx,j);
        } else if (cy==y) {
            int sx = (cx<x)? 1 : -1;
            for (int i=cx+sx; i!=x+sx; i+=sx) append(i,cy);
        } else {
            // not used
        }
    };

    append(Sx, L); // start

    auto sweepRow = [&](int row, int startSide){ // startSide 0:L, 1:R; sweep to the other side within [L..R]
        if (startSide==0) {
            // ensure at (row, L)
            moveLine(row, L);
            // sweep to R
            for (int y=L+1;y<=R;y++) append(row,y);
            return 1; // end at R
        } else {
            // ensure at (row, R)
            moveLine(row, R);
            // sweep to L
            for (int y=R-1;y>=L;y--) append(row,y);
            return 0; // end at L
        }
    };

    int dir = chosenDir;
    int endSide = 1; // after first sweep of Sx starting at L we end at R -> side=1
    // Sweep starting row Sx from L to R
    // We are at (Sx,L) already; move horizontally to R
    for (int y=L+1;y<=R;y++) append(Sx,y);
    endSide = 1; // R

    int E1 = (dir==+1)? n : 1;
    // First phase within required area
    for (int i = Sx+dir; (dir==+1)? (i<=E1) : (i>=E1); i+=dir) {
        // move vertically within end column
        int endCol = (endSide==1)? R : L;
        moveLine(i, endCol);
        // sweep row i to other end
        if (endSide==1) {
            // at R, sweep to L
            for (int y=R-1;y>=L;y--) append(i,y);
            endSide = 0;
        } else {
            // at L, sweep to R
            for (int y=L+1;y<=R;y++) append(i,y);
            endSide = 1;
        }
    }

    // Second phase if needed
    int remainStart = Sx - dir;
    if ((dir==+1 && Sx>1) || (dir==-1 && Sx<n)) {
        // need to jump via outside column at side 'endSide'
        int corridorCol = (endSide==1)? (R+1) : (L-1);
        // move to corridor
        int edgeRow = E1;
        moveLine(edgeRow, (endSide==1)? R : L);
        moveLine(edgeRow, corridorCol);
        // move along corridor to remainStart
        moveLine(remainStart, corridorCol);
        // enter required area at this row from corridor side
        int enterCol = (endSide==1)? R : L;
        moveLine(remainStart, enterCol);
        // sweep this row to other side
        if (endSide==1) {
            for (int y=R-1;y>=L;y--) append(remainStart,y);
            endSide = 0;
        } else {
            for (int y=L+1;y<=R;y++) append(remainStart,y);
            endSide = 1;
        }
        // Continue within required area for remaining rows
        for (int i = remainStart - dir; (dir==+1)? (i>=1) : (i<=n); i-=dir) {
            int endCol = (endSide==1)? R : L;
            moveLine(i, endCol);
            if (endSide==1) {
                for (int y=R-1;y>=L;y--) append(i,y);
                endSide = 0;
            } else {
                for (int y=L+1;y<=R;y++) append(i,y);
                endSide = 1;
            }
        }
    }

    // Verify that all required cells are visited exactly once
    for (int x=1;x<=n;x++) {
        for (int y=L;y<=R;y++) {
            if (!vis[x][y]) {
                // Should not happen
                cout << "NO\n";
                return 0;
            }
        }
    }

    cout << "YES\n";
    cout << path.size() << "\n";
    for (auto &p: path) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}