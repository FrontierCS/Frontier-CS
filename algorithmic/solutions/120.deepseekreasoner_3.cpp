#include <cstdio>
#include <vector>
#include <cassert>
#include <algorithm>

using namespace std;

const int N = 100;
bool adj[N+1][N+1]; // 1-indexed adjacency matrix

int query(int a, int b, int c) {
    printf("? %d %d %d\n", a, b, c);
    fflush(stdout);
    int ans;
    scanf("%d", &ans);
    return ans;
}

void answer() {
    printf("!\n");
    for (int i = 1; i <= N; i++) {
        for (int j = 1; j <= N; j++) {
            putchar(adj[i][j] ? '1' : '0');
        }
        putchar('\n');
    }
    fflush(stdout);
}

int main() {
    // Step 1: Determine edges among vertices 1,2,3,4 using 4 queries.
    int q123 = query(1,2,3);
    int q124 = query(1,2,4);
    int q134 = query(1,3,4);
    int q234 = query(2,3,4);

    // Variables: e12, e13, e14, e23, e24, e34
    int e12=0, e13=0, e14=0, e23=0, e24=0, e34=0;
    // Brute-force over 2^6 possibilities
    for (int mask = 0; mask < 64; mask++) {
        int b12 = (mask>>0)&1;
        int b13 = (mask>>1)&1;
        int b14 = (mask>>2)&1;
        int b23 = (mask>>3)&1;
        int b24 = (mask>>4)&1;
        int b34 = (mask>>5)&1;
        if (b12 + b13 + b23 != q123) continue;
        if (b12 + b14 + b24 != q124) continue;
        if (b13 + b14 + b34 != q134) continue;
        if (b23 + b24 + b34 != q234) continue;
        e12 = b12; e13 = b13; e14 = b14; e23 = b23; e24 = b24; e34 = b34;
        break;
    }
    adj[1][2] = adj[2][1] = e12;
    adj[1][3] = adj[3][1] = e13;
    adj[1][4] = adj[4][1] = e14;
    adj[2][3] = adj[3][2] = e23;
    adj[2][4] = adj[4][2] = e24;
    adj[3][4] = adj[4][3] = e34;

    // S is the set of vertices already processed
    vector<int> S = {1,2,3,4};

    // Step 2: Process vertices 5..100
    for (int v = 5; v <= N; v++) {
        int m = S.size();
        // We'll determine edges from v to all vertices in S.
        // Use vertex S[0] as the reference.
        int s0 = S[0];
        vector<int> d(m); // d[i] will store the value (query answer - adj[s0][S[i]]) for i>0
        // For i from 1 to m-1, query (v, s0, S[i])
        for (int i = 1; i < m; i++) {
            int a = S[i];
            int r = query(v, s0, a);
            d[i] = r - adj[s0][a]; // this equals (edge v-s0) + (edge v-a)
        }
        // Also query (v, S[1], S[2]) to get an equation not involving s0
        int s1 = S[1], s2 = S[2];
        int r23 = query(v, s1, s2);
        int d23 = r23 - adj[s1][s2]; // equals (edge v-s1) + (edge v-s2)

        // Now we have:
        // Let x0 = edge v-s0
        // For i>=1, let xi = edge v-S[i]
        // We have: x0 + xi = d[i] for i=1..m-1
        // And: x1 + x2 = d23
        // From i=1 and i=2: x1 = d[1] - x0, x2 = d[2] - x0
        // Substitute into x1+x2 = d23:
        // (d[1] - x0) + (d[2] - x0) = d23  =>  d[1]+d[2] - 2*x0 = d23
        // So x0 = (d[1] + d[2] - d23) / 2
        int x0 = (d[1] + d[2] - d23) / 2;
        // Sanity check: x0 should be 0 or 1
        assert(x0 == 0 || x0 == 1);
        adj[v][s0] = adj[s0][v] = x0;
        for (int i = 1; i < m; i++) {
            int xi = d[i] - x0;
            assert(xi == 0 || xi == 1);
            int a = S[i];
            adj[v][a] = adj[a][v] = xi;
        }
        S.push_back(v);
    }

    answer();
    return 0;
}