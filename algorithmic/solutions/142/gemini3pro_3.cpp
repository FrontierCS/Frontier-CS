#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Represents the state of the poles
struct State {
    int n, m;
    vector<vector<int>> poles;
    vector<pair<int, int>> operations;

    State(int n, int m) : n(n), m(m) {
        poles.resize(n + 2); // 1-based indexing, n+1 is initially empty
    }

    void move(int from, int to) {
        if (poles[from].empty()) return; // Should not happen in valid logic
        int ball = poles[from].back();
        poles[from].pop_back();
        poles[to].push_back(ball);
        operations.push_back({from, to});
    }

    // Returns the count of balls with color 'c' in pole 'p'
    int countColor(int p, const vector<int>& colors) {
        int cnt = 0;
        for (int b : poles[p]) {
            for (int c : colors) {
                if (b == c) {
                    cnt++;
                    break;
                }
            }
        }
        return cnt;
    }
    
    // Check if color c is in target set
    bool isTarget(int color, const vector<int>& targets) {
        for(int t : targets) if(color == t) return true;
        return false;
    }
};

void smartExchange(State& state, int u, int v, int emptyPole, const vector<int>& L_colors) {
    // Goal: Move L-type balls from v to u, and R-type balls from u to v.
    // L-type is defined by L_colors. R-type is anything else.
    
    auto isL = [&](int c) {
        for(int x : L_colors) if(x == c) return true;
        return false;
    };

    int cntR_u = 0;
    for(int c : state.poles[u]) if(!isL(c)) cntR_u++;
    
    int cntL_v = 0;
    for(int c : state.poles[v]) if(isL(c)) cntL_v++;
    
    int k = min(cntR_u, cntL_v);
    if (k == 0) return;

    if (cntR_u <= cntL_v) {
        // Strategy: Unpack u.
        // Move all from u to emptyPole.
        while(!state.poles[u].empty()) {
            state.move(u, emptyPole);
        }
        // Filter back L balls to u. R balls stay in emptyPole.
        // emptyPole is a stack, so we process from top.
        // We need to put L balls in u. 
        // But R balls are blocking? No, we need to iterate through emptyPole.
        // We can move balls from emptyPole. If L -> u. If R -> v? v is full.
        // Wait, standard strategy: 
        // Move all u to emptyPole. 
        // Now emptyPole has the balls. Top of emptyPole is bottom of u.
        // We can't access arbitrary balls.
        
        // Correct implementation of Unpack u strategy:
        // 1. Move all u -> emptyPole.
        // 2. Move L balls from emptyPole -> u. 
        //    R balls: we want them in v eventually. But v is full.
        //    So we must leave them in emptyPole?
        //    If we leave them in emptyPole, they are buried.
        //    Wait, we simply move ALL L balls from emptyPole to u.
        //    For R balls, we move them to... u? No.
        //    If we encounter R ball in emptyPole, we must put it somewhere to access below.
        //    We can put it in v? v is full.
        //    This requires v to have space. 
        
        // Actually, the "SmartExchange" logic derived derived:
        // We need to coordinate movements.
        
        // Let's restart the "Unpack u" logic properly.
        // We want u to have its original L's + k new L's from v.
        // v to have its original R's + k new R's from u.
        
        // Step 1: Move all u to emptyPole.
        // Step 2: Iterate v (top to bottom).
        //    If ball is L (and we need more L's): move to u.
        //    If ball is R: move to emptyPole.
        //    Constraint: emptyPole must not overflow.
        //    Condition cntR_u <= cntL_v ensures safety.
        // Step 3: Now u has all required L's (mixed with nothing? No, u only got L's).
        //         emptyPole has all R's (from u and v).
        //         Move all from emptyPole to v.
        
        // To implement Step 2 (Iterate v):
        // We simply operate on v.
        // While v is not empty:
        //    ball = top(v).
        //    if isL(ball): move v -> u.
        //    else: move v -> emptyPole.
        // EXCEPT: We only want to exchange k balls.
        // u initially had (m - cntR_u) L balls.
        // We want to add k L balls from v. Total L in u = m - cntR_u + k.
        // v has cntL_v L balls. We take k. Remaining L in v = cntL_v - k.
        // We should stop when u is full? Or when we processed enough?
        
        // The previous check showed emptyPole max usage is safe.
        // However, we need to preserve the balls we DON'T want to swap.
        // i.e., u's original L's should go back to u.
        // v's original R's should go back to v.
        
        // Correct sequence:
        // 1. u -> emptyPole.
        // 2. Filter emptyPole:
        //    While emptyPole not empty:
        //      if isL(top): move to u.
        //      else: keep in emptyPole? No, we can't skip.
        //      If we encounter R in emptyPole, we must move it to v? v is full.
        //      So this approach "Filter u first" is problematic because v is full.
        
        // Alternative: Use v's space. But v is full.
        // But we emptied u! So we have u as buffer (size m).
        // 1. Move all u -> emptyPole.
        // 2. Process v:
        //    For each ball in v:
        //      If isL(ball): move to u.
        //      Else (isR): move to emptyPole.
        //    Wait, emptyPole has u's balls.
        //    We add v's R balls to emptyPole.
        //    We add v's L balls to u.
        //    Also, we need u's L balls back in u.
        //    u's L balls are buried in emptyPole.
        //    This order is wrong.
        
        // We need u's L balls in u AND v's L balls in u.
        // u's L balls are in emptyPole.
        // v's L balls are in v.
        
        // Correct Algorithm:
        // 1. Move all balls from u to emptyPole.
        //    Count L's in u as we move? We know it.
        // 2. We want to move all L's from emptyPole to u.
        //    AND move k L's from v to u.
        //    AND put all R's to v.
        //    Problem: L's in emptyPole are mixed with R's.
        
        // Let's use the property cntR_u <= cntL_v.
        // Total L in u is m - cntR_u.
        // We need to fill u with k more L's from v.
        
        // Let's move balls from v to u (k L's).
        // But v has R's on top probably.
        // Move R's from v to emptyPole. 
        // Move L's from v to u.
        // Does emptyPole fit?
        // emptyPole has m balls (from u).
        // We add R's from v.
        // Max size = m + (R's in v before k L's).
        // R's in v total = m - cntL_v.
        // Max size <= m + m - cntL_v.
        // This is > m. Overflow.
        
        // Wait, the safety condition was derived assuming we DON'T hold u's R balls?
        // Ah, if we process u, we separate u into L (to u) and R (to v).
        // But we can't send R to v immediately.
        
        // Let's look at the constraint again.
        // We have 2*10^6 ops.
        // We can rotate u using emptyPole to bring L's to top?
        // "Bubble Sort" inside stack?
        // To bring L's to bottom of u:
        // u -> emptyPole.
        // for ball in emptyPole: if L -> u, else -> v (if v empty).
        
        // We must process u and v together.
        // Let's rely on the primitive:
        // "Swap top of u (if R) with top of v (if L)" using emptyPole.
        // This is efficient.
        // While u has R and v has L:
        //   Bring R to top of u.
        //   Bring L to top of v.
        //   Swap.
        
        // Bring R to top of u:
        //   Count depth of first R.
        //   Move top balls to emptyPole.
        //   Move R to v? No, swap requires space.
        //   This is messy.
        
        // Back to the "Unpack" strategy which works if we filter correctly.
        // The issue is mixing from two sources (u and v) to two destinations (u and v).
        // With 1 buffer.
        
        // Let's try to clear u of R balls (move to v) and take L balls from v.
        // Condition: cntR_u <= cntL_v.
        // We simply move ALL from u to emptyPole.
        // Then move ALL from v.
        //   If L -> u.
        //   If R -> emptyPole.
        // This requires emptyPole to hold (u's balls) + (v's R balls).
        // Max balls = m + (m - cntL_v). Overflow.
        
        // UNLESS we filter u's balls first.
        // u -> emptyPole.
        // emptyPole -> u (only L's).
        // R's stay in emptyPole? Can't skip.
        // R's -> v? v is full.
        
        // What if we use the OTHER poles?
        // We are at a recursion step.
        // We have poles in L_group and R_group.
        // We are processing u in L_group, v in R_group.
        // Are there other poles?
        // Yes, if n > 2.
        // If we have ANY other pole w, we can use it?
        // w is full.
        // But we can use the top of w as temp storage for 1 ball?
        // No, capacity strict m.
        
        // Let's go back to basics.
        // We have n+1 poles.
        // To sort:
        // Iterate colors c = 1 to n.
        // Isolate color c into pole c.
        // This reduces problem to: Collect color c into pole c.
        // Source poles j > c.
        // For each j, we want to move c-balls from j to c, and non-c from c to j.
        // Let's implement `ExtractColor(target, source, empty, color)`.
        
        // `ExtractColor(A, B, E, color)`
        // A has mixed. B has mixed.
        // Goal: Move `color` from B to A. Move `non-color` from A to B.
        // Count `k` instances of `color` in B.
        // 1. Count `non-color` in A.
        //    Find the `k`-th `non-color` ball in A from top?
        //    Actually, just move `non-color` from A to E, keep `color` in A?
        //    Can't reorder easily.
        
        // Implementation that works (Codeforces 1261C style):
        // Collect all 'color' from B to A.
        // Count 'color' in B: k.
        // Move all balls from A to E.
        //   Record which are 'color' (keep count).
        //   Actually, we want A to be empty.
        // Scan B.
        //   If ball is 'color': move B -> A.
        //   Else: move B -> E.
        //     Check overflow: E has A's balls + B's non-color balls.
        //     Size = m + (m - k). Overflow if k < m.
        //     This simple scan overflows.
        
        // However, we can perform this partially!
        // We only have space m in E.
        // A is empty.
        // E has m balls.
        // We can put balls from B into A (if color) or E (if non-color).
        // But E is full.
        // So we can only put into A.
        // But we want non-color to go to E/B.
        
        // Okay, use A as buffer for non-color of B.
        // 1. A -> E.
        // 2. Iterate B.
        //    If 'color': move B -> A.
        //    If 'non-color': move B -> A.
        //    Wait, everything to A? Then we just inverted B to A. Pointless.
        
        // Let's assume we can swap tops.
        // Algorithm:
        // While (A has non-color AND B has color):
        //   Bring non-color to top of A.
        //   Bring color to top of B.
        //   Swap (A->E, B->A, E->B).
        // To bring X to top of S:
        //   Count depth d.
        //   Move d-1 balls to E.
        //   But E must be empty.
        //   If we use E to swap, E must be empty.
        //   So we can't store d-1 balls in E AND perform swap.
        
        // Actually, "Ball Game" constraints usually allow O(N^2) or O(N M).
        // The operations are 2*10^6. N*M = 20000.
        // 100 ops per ball.
        // This is enough to dismantle a stack to get 1 ball.
        // To get ball at depth d in A (and keep others):
        // Move d-1 to E.
        // Move target to B (temp).
        // Move d-1 back to A.
        // Move target B -> A.
        // Target is now at top.
        // Cost: 2d. Max 2m.
        // Doing this for every swap: 2m * (number of balls).
        // Total balls to swap could be N*M/2.
        // Total ops: m * N * m = N m^2.
        // 50 * 400^2 = 8,000,000. Too slow (Limit 2M).
        // But average depth is m/2.
        // And we don't swap every ball.
        // Also k (swaps per pair) is small on average?
        
        // Wait, 2M is generous but not infinite.
        // But we can optimize "Bring to top".
        // If we have multiple 'bad' balls, we bring the topmost bad ball.
        // Average depth of topmost bad ball is small if there are many bad balls.
        // If few bad balls, we do few ops.
        // So complexity is roughly Sum of depths of bad balls.
        // Worst case: 1 bad ball at bottom.
        
        // Let's implement the "Swap Tops" strategy.
        // 1. Find topmost non-L in u (depth d1).
        // 2. Find topmost L in v (depth d2).
        // 3. Bring them to surface.
        //    To bring ball at d1 in u to top:
        //       Move d1-1 balls to E.
        //       Move target (u->v temporarily? No v full).
        //       Move target u->empty? No E has stuff.
        //    We need a place for the d1-1 balls. E is the place.
        //    We need a place for the target. E is occupied.
        //    This is the deadlock.
        
        // Solution:
        // We process u. Move non-targets to E. Keep targets in u?
        // No, stack.
        // Move top d1-1 (targets) to E.
        // Move bad ball to v? v full.
        
        // OK, Use the fact that we process the whole column at once.
        // We want to partition u and v.
        // Count required swaps k.
        // Step 1: Move k non-L from u to v.
        //         Move k L from v to u.
        // Execute:
        // 1. Move all balls from u to E.
        //    (u is empty).
        // 2. Iterate v.
        //    If ball is L: move v -> u.
        //    If ball is R: move v -> E? (Check overflow).
        //    If overflow risk: move v -> u (temporarily).
        // 3. Now v is empty? Or processed.
        //    Move balls back to correct places.
        
        // Revised "Unpack" with overflow handling.
        // Case A: cntR_u <= cntL_v.
        //   1. u -> E. (E has u's balls).
        //   2. v -> u (only L's). v -> E (R's).
        //      Check max E: cntR_u + (R's in v).
        //      Max E = cntR_u + m - cntL_v <= m. Safe.
        //   3. Now u has L's from v.
        //      E has (u's balls) + (v's R balls).
        //      We want to fill u with u's L balls (from E).
        //      And put R balls (from u and v) into v.
        //   4. Process E (top down).
        //      E contains u's balls (bottom) and v's R balls (top).
        //      Top part (v's R) -> v.
        //      Bottom part (u's balls):
        //         If L -> u.
        //         If R -> v.
        //   Done.
        
        // Case B: cntR_u > cntL_v.
        //   Use symmetric logic. Unpack v.
        //   1. v -> E.
        //   2. u -> v (only R's). u -> E (L's).
        //      Max E = cntL_v + (L's in u).
        //      Max E = cntL_v + m - cntR_u < m. Safe.
        //   3. Now v has R's from u.
        //      E has (v's balls) + (u's L balls).
        //      Process E:
        //      Top part (u's L) -> u.
        //      Bottom part (v's balls):
        //         If R -> v.
        //         If L -> u.
        //   Done.

        if (cntR_u <= cntL_v) {
            // Case A
            while(!state.poles[u].empty()) state.move(u, emptyPole);
            
            // Filter v
            // We need to move exactly k L's from v to u.
            // But wait, u needs to be FULL or contain specific set?
            // We just want to move L's.
            // Move balls from v.
            int moved_L = 0;
            // We need to handle the balls remaining in v if any.
            // Actually we should empty v completely?
            // The logic assumes we process ALL balls in v.
            // v will be empty. u will be partially full. E has the rest.
            int v_orig_size = state.poles[v].size(); // m
            for(int i=0; i<v_orig_size; ++i) {
                int b = state.poles[v].back();
                if (isL(b)) {
                    state.move(v, u);
                    moved_L++;
                } else {
                    state.move(v, emptyPole);
                }
            }
            
            // Now reconstruct.
            // E has: Bottom [u_orig] Top [v_R_balls]
            // u has: [v_L_balls]
            // We want u to have [v_L_balls] + [u_L_balls]
            // v to have [v_R_balls] + [u_R_balls]
            
            // Move v_R_balls from E back to v.
            // How many? v_orig_size - moved_L.
            int v_R_count = v_orig_size - moved_L;
            for(int i=0; i<v_R_count; ++i) {
                state.move(emptyPole, v);
            }
            
            // Now E has [u_orig].
            // Process u_orig.
            int u_orig_size = state.poles[emptyPole].size();
            for(int i=0; i<u_orig_size; ++i) {
                int b = state.poles[emptyPole].back();
                if (isL(b)) state.move(emptyPole, u);
                else state.move(emptyPole, v);
            }
        } else {
            // Case B: Unpack v
            while(!state.poles[v].empty()) state.move(v, emptyPole);
            
            int moved_R = 0;
            int u_orig_size = state.poles[u].size();
            for(int i=0; i<u_orig_size; ++i) {
                int b = state.poles[u].back();
                if (!isL(b)) {
                    state.move(u, v);
                    moved_R++;
                } else {
                    state.move(u, emptyPole);
                }
            }
            
            // E has: Bottom [v_orig] Top [u_L_balls]
            // v has: [u_R_balls]
            
            // Move u_L_balls from E back to u.
            int u_L_count = u_orig_size - moved_R;
            for(int i=0; i<u_L_count; ++i) {
                state.move(emptyPole, u);
            }
            
            // Process v_orig in E.
            int v_orig_size = state.poles[emptyPole].size();
            for(int i=0; i<v_orig_size; ++i) {
                int b = state.poles[emptyPole].back();
                if (!isL(b)) state.move(emptyPole, v);
                else state.move(emptyPole, u);
            }
        }
    }
}

void solve(State& state, vector<int> poles, vector<int> colors) {
    if (colors.size() <= 1) return;
    if (poles.empty()) return;

    // Split colors
    int mid = colors.size() / 2;
    vector<int> L_colors(colors.begin(), colors.begin() + mid);
    vector<int> R_colors(colors.begin() + mid, colors.end());

    // Assign poles. Capacity needed = count of balls of L_colors.
    // Total balls = n * m.
    // Count total balls for L_colors.
    // Actually, each color has m balls. So L_colors need |L_colors| poles.
    int num_L = L_colors.size();
    
    vector<int> L_poles, R_poles;
    for(int i=0; i<num_L; ++i) L_poles.push_back(poles[i]);
    for(size_t i=num_L; i<poles.size(); ++i) R_poles.push_back(poles[i]);

    int emptyPole = state.n + 1; // Assuming n+1 is always the empty pole available globally
    // But wait, the empty pole location might change if we use it? 
    // No, we always return to state where emptyPole is empty.
    
    // Partition
    // Iterate L_poles and R_poles to swap misplaced balls
    size_t lp = 0, rp = 0;
    while (lp < L_poles.size() && rp < R_poles.size()) {
        int u = L_poles[lp];
        int v = R_poles[rp];
        
        // Perform exchange
        smartExchange(state, u, v, emptyPole, L_colors);
        
        // Check if u is clean (only L balls)
        bool u_clean = true;
        for(int c : state.poles[u]) {
            bool is_L = false;
            for(int lc : L_colors) if(c==lc) is_L = true;
            if(!is_L) { u_clean = false; break; }
        }
        if(u_clean) lp++;
        
        // Check if v is clean (only R balls)
        bool v_clean = true;
        for(int c : state.poles[v]) {
            bool is_R = true;
            for(int lc : L_colors) if(c==lc) is_R = false;
            if(!is_R) { v_clean = false; break; }
        }
        if(v_clean) rp++;
    }

    solve(state, L_poles, L_colors);
    solve(state, R_poles, R_colors);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    State state(n, m);
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int c;
            cin >> c;
            state.poles[i].push_back(c);
        }
    }

    vector<int> poles(n);
    iota(poles.begin(), poles.end(), 1);
    vector<int> colors(n);
    iota(colors.begin(), colors.end(), 1);

    solve(state, poles, colors);

    cout << state.operations.size() << "\n";
    for (auto& op : state.operations) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}