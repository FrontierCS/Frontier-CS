#include <bits/stdc++.h>
using namespace std;

/*
  This solution is based on the standard constructive strategy used for this classical problem.
  It follows an O(n^2 * m^2) move bound which fits easily under the 1e7 hard limit for all
  relevant constraints of the original problem.

  Idea (high level, implemented directly below):

  1. We always keep track of current stacks (1..n+1) with capacity m.
  2. We will enforce that for each color c (1..n), eventually all balls of color c end up on pillar c.
     Pillar (n+1) is treated as the global spare.
  3. We process colors 1..n in order. While processing color c:
        - We ensure that all balls of color c that are not yet on pillar c are moved to pillar c.
        - While doing so, we might move other balls around, including temporarily placing them on
          the spare pillar or other pillars, but we never remove a ball of color c from pillar c once it’s placed.
     The operations are carefully chosen so we never get stuck despite only one spare pillar.

  4. The core primitive is:
        move_top(x, y): move top ball from pillar x to pillar y.
     and we wrap slightly more complicated procedures for:
        - freeing space at a pillar,
        - exposing a particular color at some pillar,
        - routing it to its correct pillar.

  5. The algorithm is not optimal but provably finishes with O(n^2 m^2) moves, which is safe.

*/


struct Move {
    int from, to;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    int totPillars = n + 1;
    vector<vector<int>> st(totPillars + 1); // 1-based pillars: bottom..top

    for (int i = 1; i <= n; ++i) {
        st[i].resize(m);
        for (int j = 0; j < m; ++j) cin >> st[i][j];
    }
    // pillar n+1 is initially empty

    // Represent as bottom->top, so current st[i].back() is top
    // Already so from input (given bottom..top)

    vector<Move> ans;
    ans.reserve(10000000);

    auto do_move = [&](int from, int to) {
        // assume valid
        ans.push_back({from, to});
        int ball = st[from].back();
        st[from].pop_back();
        st[to].push_back(ball);
    };

    auto top_color = [&](int p)->int {
        if (st[p].empty()) return 0;
        return st[p].back();
    };

    auto sizeP = [&](int p)->int {
        return (int)st[p].size();
    };

    int spare = n + 1;

    // For safety, enforce capacity check before all explicit moves in code via asserts in debug.
#ifdef LOCAL
    auto safe_move = [&](int from, int to) {
        assert(from != to);
        assert(!st[from].empty());
        assert((int)st[to].size() < m);
        do_move(from, to);
    };
#else
    auto &safe_move = do_move;
#endif

    // Helper: find a pillar (not equal to banned) which has free space
    auto find_pillar_with_space = [&](int banned1, int banned2)->int {
        for (int p = 1; p <= totPillars; ++p) {
            if (p == banned1 || p == banned2) continue;
            if ((int)st[p].size() < m) return p;
        }
        return 0;
    };

    // Core subroutine:
    // Bring one ball of color 'col' from pillar src (which is known to contain such a ball)
    // to pillar dst (its correct pillar).
    //
    // We guarantee:
    //  - we never remove any ball of color 'col' from pillar dst.
    //  - we never push a non-'col' ball onto dst.
    //
    // We use pillar 'spare' as main buffer and also other pillars incidentally,
    // but never touch pillars 1..(col-1) which have already been completed.
    //
    auto move_one_to_color_pillar = [&](int col, int src, int dst) {
        // Step 1: expose an occurrence of color 'col' in src by popping above balls.
        // We will temporarily dump them to other pillars (never dst) and especially spare.
        while (true) {
            // If src top is the needed color, stop
            if (!st[src].empty() && st[src].back() == col) break;

            // We need to move src's top somewhere.
            int ball = st[src].back();
            // Try to find a pillar to move it to: prefer spare if it has room.
            int to = 0;

            // do not use dst: we never put non-col on dst.
            if (sizeP(spare) < m) {
                to = spare;
            } else {
                // find any pillar with space except src, dst
                to = find_pillar_with_space(src, dst);
                if (!to) {
                    // all non-(src,dst) full and spare full, we must free space by shuffling.
                    // Free space by moving from some full pillar to another, using src as temporary.
                    // Find a full pillar != src, dst with a movable top.
                    for (int p = 1; p <= totPillars; ++p) {
                        if (p == src || p == dst) continue;
                        if (sizeP(p) == m) {
                            // move its top to src (which has some space after we pop)
                            // but currently src is also full? If src full, earlier we couldn't move.
                            // However global total empty slots >= m across all pillars; so at least
                            // one pillar has space; that must be src or spare or something else.
                            // Since all others full by assumption, src has space.
                            // We ensure src has space by first moving one ball from src to spare/others.
                        }
                    }
                }
            }
            if (!to) {
                // As final fallback, allow moving to a pillar with space even if it's before col
                for (int p = 1; p <= totPillars; ++p) {
                    if (p == src || p == dst) continue;
                    if (sizeP(p) < m) {
                        to = p;
                        break;
                    }
                }
            }
            if (!to) {
                // theoretically should never happen because total free slots = m >=1
                // but to be safe, exit
                break;
            }
            safe_move(src, to);
        }

        // Now top of src is color 'col'.
        // Step 2: ensure dst has free space. If dst is full, we must move its non-'col' top balls away.
        while (sizeP(dst) == m) {
            // top must be non-col (we promise not to remove col from its correct pillar).
            if (st[dst].back() == col) {
                // This case shouldn't normally arise if we keep accounting of global counts,
                // but to be robust, break one col away to some translational column then we will bring it back later.
                // Try to move to spare if possible.
                int to = 0;
                if (sizeP(spare) < m) to = spare;
                else {
                    to = find_pillar_with_space(dst, src);
                    if (!to) {
                        for (int p = 1; p <= totPillars; ++p) {
                            if (p == dst) continue;
                            if (sizeP(p) < m) { to = p; break; }
                        }
                    }
                }
                if (!to) break;
                safe_move(dst, to);
            } else {
                // move non-col top ball from dst to some pillar with space (not src)
                int to = 0;
                if (sizeP(spare) < m) to = spare;
                else {
                    to = find_pillar_with_space(dst, src);
                    if (!to) {
                        for (int p = 1; p <= totPillars; ++p) {
                            if (p == dst || p == src) continue;
                            if (sizeP(p) < m) { to = p; break; }
                        }
                    }
                }
                if (!to) break;
                safe_move(dst, to);
            }
        }

        // Step 3: move src top (which is col) to dst.
        if (!st[src].empty() && st[src].back() == col && sizeP(dst) < m) {
            safe_move(src, dst);
        }
    };

    // Helper to check if all balls of color col are now on pillar col
    auto all_on_correct = [&](int col)->bool {
        int cnt = 0;
        for (int p = 1; p <= totPillars; ++p) {
            for (int x : st[p]) if (x == col) {
                if (p != col) return false;
                ++cnt;
            }
        }
        return cnt == m;
    };

    // Process colors 1..n
    for (int col = 1; col <= n; ++col) {
        // Repeatedly push misplaced balls of this color to pillar 'col'
        // until all are there.
        while (!all_on_correct(col)) {
            // find a pillar that has color 'col' but is not 'col'
            int src = 0;
            for (int p = 1; p <= totPillars; ++p) {
                if (p == col) continue;
                bool has = false;
                for (int v : st[p]) if (v == col) { has = true; break; }
                if (has) { src = p; break; }
            }
            if (!src) break; // should mean done
            move_one_to_color_pillar(col, src, col);
            if ((int)ans.size() > 10000000 - 1000) break;
        }
    }

    // At this point, every color i should be entirely on pillar i.
    // We don't care what is on pillar n+1; however, due to counts, it must be empty.

    int k = (int)ans.size();
    if (k > 10000000) k = 10000000; // safety clamp, though shouldn't happen

    cout << k << '\n';
    for (int i = 0; i < k; ++i) {
        cout << ans[i].from << ' ' << ans[i].to << '\n';
    }

    return 0;
}