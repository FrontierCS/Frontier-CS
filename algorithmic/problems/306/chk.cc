#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // ---- read input ----
    int n = inf.readInt();
    int e = inf.readInt();

    vector<int> eu(e+1), ev(e+1), ea(e+1), eb(e+1), ec(e+1);
    vector<vector<pair<int,int>>> adj(n+1);

    for (int j = 1; j <= e; j++) {
        eu[j] = inf.readInt();
        ev[j] = inf.readInt();
        ea[j] = inf.readInt();
        eb[j] = inf.readInt();
        ec[j] = inf.readInt();
        adj[eu[j]].push_back({ev[j], j});
        adj[ev[j]].push_back({eu[j], j});
    }

    int m = inf.readInt();
    vector<int> day_r(m), day_L(m);
    vector<vector<int>> depot_island(m), depot_val(m);

    long long B = 0;
    for (int i = 0; i < m; i++) {
        day_r[i] = inf.readInt();
        day_L[i] = inf.readInt();
        depot_island[i].resize(day_r[i]);
        depot_val[i].resize(day_r[i]);
        for (int t = 0; t < day_r[i]; t++) {
            depot_island[i][t] = inf.readInt();
            depot_val[i][t] = inf.readInt();
            B += depot_val[i][t];
        }
    }

    // ---- read participant output ----

    int x = ouf.readInt(0, e, "number of rigged bridges x");

    vector<bool> is_rigged(e+1, false);
    long long InstallCost = 0;

    {
        set<int> seen;
        for (int i = 0; i < x; i++) {
            int bid = ouf.readInt(1, e, "rigged bridge ID");
            if (seen.count(bid))
                quitf(_wa, "Duplicate rigged bridge ID: %d", bid);
            seen.insert(bid);
            is_rigged[bid] = true;
            InstallCost += ea[bid];
        }
    }

    // detonation counts over the whole campaign
    vector<int> det_count(e+1, 0);

    long long BlastCost = 0;
    long long Harvested = 0;

    // BFS reuse structures
    vector<bool> visited(n+1, false);
    vector<bool> edge_removed(e+1, false);

    for (int i = 0; i < m; i++) {
        int d = ouf.readInt(0, day_L[i], "number of detonations on day");

        vector<int> today_det;
        {
            set<int> seen_today;
            for (int k = 0; k < d; k++) {
                int bid = ouf.readInt(1, e, "detonated bridge ID");
                if (seen_today.count(bid))
                    quitf(_wa, "Duplicate detonated bridge ID %d on day %d", bid, i+1);
                seen_today.insert(bid);

                if (!is_rigged[bid])
                    quitf(_wa, "Bridge %d detonated on day %d but not rigged", bid, i+1);

                today_det.push_back(bid);
                det_count[bid]++;

                // Check per-bridge detonation limit
                if (det_count[bid] > ec[bid])
                    quitf(_wa, "Bridge %d detonated %d times but limit is %d",
                          bid, det_count[bid], ec[bid]);

                BlastCost += eb[bid];
                edge_removed[bid] = true;
            }
        }

        // BFS from node 1 over non-removed edges
        if (day_r[i] > 0) {
            vector<int> reached;
            queue<int> bfs;
            bfs.push(1);
            visited[1] = true;
            reached.push_back(1);
            while (!bfs.empty()) {
                int u = bfs.front(); bfs.pop();
                for (auto [w, eid] : adj[u]) {
                    if (!visited[w] && !edge_removed[eid]) {
                        visited[w] = true;
                        reached.push_back(w);
                        bfs.push(w);
                    }
                }
            }
            for (int t = 0; t < day_r[i]; t++) {
                int isl = depot_island[i][t];
                int val = depot_val[i][t];
                if (visited[isl]) {
                    Harvested += val;
                }
            }
            // reset visited
            for (int node : reached) visited[node] = false;
        }

        // reset edge_removed for today's detonations
        for (int bid : today_det) edge_removed[bid] = false;
    }

    // Require end-of-file: reject extra trailing tokens
    if (!ouf.seekEof())
        quitf(_wa, "Extra output after the last day line");

    long long F = InstallCost + BlastCost + Harvested;

    // Score formula: Score_test = min(1000, 100 * B / max(1, F))
    double score_1000 = min(1000.0, 100.0 * (double)B / (double)max(1LL, F));
    double ratio = score_1000 / 1000.0;

    quitp(ratio,
          "OK. InstallCost=%lld BlastCost=%lld Harvested=%lld F=%lld B=%lld "
          "Score=%.4f Ratio: %.6f",
          InstallCost, BlastCost, Harvested, F, B,
          score_1000, ratio);
}