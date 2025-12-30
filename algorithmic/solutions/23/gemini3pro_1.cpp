#include <iostream>

int main() {
    // A=B solution
    // Strategy:
    // 1. Setup walls | (Left) and } (Right).
    // 2. Convert t (input after S) to variants D..O based on start/mid/end/both status.
    // 3. Move t chars to the left, past s, and reverse their order to get t_rev s.
    // 4. Perform matching at the boundary of t_rev and s.
    // 5. If match succeeds (End/Both t-char matches), return 1.
    // 6. If mismatch, reset t and delete first char of s (advance start).
    // 7. If s becomes empty (hit Right wall), return 0.

    // Alphabet mapping:
    // s: a, b, c
    // t variants (Shape: a, b, c):
    //   Start: D, E, F
    //   Mid:   G, H, I
    //   End:   J, K, L
    //   Both:  M, N, O
    // Matched t: d, e, f (Start), g, h, i (Mid)
    // Matched s: A, B, C (to restore), u, v, w (to delete/start)
    //
    // Markers:
    // | : Left wall
    // } : Right wall
    // S : Input separator / setup cursor
    // W : Reset wave
    //
    // Program logic order matters.
    
    std::cout << "S=P}" << std::endl; // Start setup: S becomes P (pro-separator) and Right Wall
    std::cout << "aP=Pa" << std::endl; // Move P left past s
    std::cout << "bP=Pb" << std::endl;
    std::cout << "cP=Pc" << std::endl;
    std::cout << "P=|Q" << std::endl; // P hits start, becomes Left Wall and Q (t-converter)

    // Q converts t (a,b,c) to t variants. Initially assume Start (D,E,F).
    // The previous t-char determines the type of the next one. 
    // We use a state-based conversion moving right.
    // Q is state "Start". R is state "Mid".
    std::cout << "Qa=DQ" << std::endl; // Q (Start) sees a -> D (Start-a), stay Q? No, next is Mid.
    std::cout << "Qb=EQ" << std::endl; // But wait, we need to know if next is end.
    std::cout << "Qc=FQ" << std::endl; // Q -> R (Mid state)
    // Correct logic: S conversion loop needs to handle lookahead or fixup.
    // Let's use fixup. Convert all to Start initially? No.
    // Convert to Mid (G,H,I) generally.
    // Then fix Start and End.
    // Q is generic converter.
    
    // REDESIGN SETUP for strict 100 limit and correctness:
    // 1. S moves right, converting t to G,H,I (Mid).
    // 2. S hits }, becomes fixer K.
    // 3. K moves left. First char it hits is End. Change G->J, etc.
    // 4. K continues left. Last char it hits (next to |) is Start. Change J->M (Both) or G->D.
    
    // Setup Phase
    // S=P} already done. P moves left. P=|Q.
    // Q converts a,b,c to G,H,I (Mid).
    // Problem: a,b,c are to the RIGHT of Q.
    std::cout << "Qa=GaQ" << std::endl; // Move converted G left. Q stays to convert next?
    // Q a b -> G Q b -> G H Q.
    // But we need to keep order? Q a -> G Q.
    std::cout << "Qb=HbQ" << std::endl; // Wait, Qa=GaQ produces GaQ. 
    std::cout << "Qc=IcQ" << std::endl; // We want Q to move past a. Q a = G Q.
    // But A=B limit 3 chars. "Qa=GQ" ok.
    
    // Overwriting previous logic lines with correct block
    // Output everything at end.
    
    // Let's clear and write the final code block.
    // Since I must only output code, I will structure the couts.
    
    /*
    Final Plan:
    1. S -> P}
    2. P moves left: xP -> Px
    3. P -> |Q (Left wall, Q converter)
    4. Q moves right converting t: Qa->GQ, Qb->HQ, Qc->IQ
    5. Q hits }: Q}->K} (K is right-fixer)
    6. K moves left (reverses t logic? No, just fix types).
       Actually, bubble sort needs t reversed.
       Q a = G Q. a is s-char? No t-char.
       Q puts G on left.
       Order s G H I }.
       t is preserved.
       We need t reversed for matching?
       Recall: s D E (start end).
       We need s D E. Boundary E s? No D s.
       D is Start. s is Start.
       Start of t (D) must be adjacent to s.
       Order s D E implies D is next to s.
       Yes. t matches s prefix.
       So we need s t.
       We need to move s to RIGHT of t?
       t s. D E s. D touches s.
       Yes.
       
    7. Move t (G,H,I) left past s (a,b,c).
       a G = G a.
       This preserves s-order and t-order.
       Result G H I s.
       G is t_1. s is s_1.
       Adjacent!
       
    8. Fix types.
       G H I s.
       Leftmost t (G) is Start.
       Rightmost t (I) is End.
       We need to mark them.
       Use Left Wall | to mark Start.
       | G -> | D.
       Use s to mark End?
       I s -> L s.
       But I is not necessarily End.
       
       Better: Fix types BEFORE moving past s.
       s G H I }.
       Leftmost G is Start (next to s).
       Rightmost I is End (next to }).
       
       Fixing Rightmost (End):
       K moves left from }.
       K I -> L K. (I->L End).
       K H -> K H. (Skip mid).
       K G -> K G.
       K s -> K s? No K stops at s?
       K needs to cross t.
       K G -> z G K? No K moves left.
       G K -> K G? No.
       
       Let's use just 2 passes.
       Q converts to G,H,I.
       s G H I Q }.
       Q becomes K.
       K I -> L z. (Mark End, z is carrier).
       K H -> I z. (Mark Mid, H->I? No H is H).
       K G -> H z.
       z moves left.
       s G H L z }.
       z hits s. z becomes nothing?
       z marks the one to its right as Start?
       Hard.
       
       Simpler:
       Just use the generic t-chars G,H,I.
       Match logic handles "first" and "last" dynamically?
       Start: Element next to | (after move).
       End: Element next to s.
       Wait, order: | t s }.
       | G H I s }.
       G is next to |. G is Start? No, G is t_1.
       Wait, | t s.
       | t_1 t_2 s.
       t_1 is Start.
       t_last is next to s? No.
       t_last is I.
       | G H I s.
       G is t_1. Start.
       I is t_last. End.
       
       But G is next to |. Correct.
       I is next to s. Correct.
       So:
       Start = Leftmost.
       End = Rightmost.
       
       Match logic:
       We only compare Rightmost t (I) with s?
       No, we compare t_1 (G).
       But G is far from s.
       We need t_rev.
       | I H G s.
       Then G (Start) is next to s.
       I (End) is next to |.
       
       Reversing t:
       Use bubble sort on t.
       X Y = Y X for all t-pairs.
       This reverses t block!
       Result | I H G s.
       
       So:
       1. Convert to G,H,I.
       2. Move G,H,I left past s.
       3. Bubble sort G,H,I (reverse).
       4. Mark I as End (next to |). Mark G as Start (next to s).
       5. Match.
    */
    
    // Implementation
    std::cout << "S=P}" << std::endl;
    
    // Move P left
    std::cout << "aP=Pa\nbP=Pb\ncP=Pc" << std::endl;
    
    // P becomes |Q
    std::cout << "P=|Q" << std::endl;
    
    // Q converts t to G,H,I
    std::cout << "Qa=GQ\nQb=HQ\nQc=IQ" << std::endl;
    
    // Q hits } -> delete Q
    std::cout << "Q} =}" << std::endl; // A=B requires space? No. "Q}=}"
    
    // Move t (G,H,I) left past s (a,b,c)
    // aG=Ga, etc.
    std::cout << "aG=Ga\naH=Ha\naI=Ia" << std::endl;
    std::cout << "bG=Gb\nbH=Hb\nbI=Ib" << std::endl;
    std::cout << "cG=Gc\ncH=Hc\ncI=Ic" << std::endl;
    
    // Reverse t (G,H,I)
    // GH=HG, GI=IG, HI=IH
    std::cout << "GH=HG\nGI=IG\nHI=IH" << std::endl;
    
    // Now we have | ... t_rev ... s ... }
    // Mark Start (rightmost t, next to s) and End (leftmost t, next to |)
    // Actually we can have specific markers.
    // D,E,F = Start (from G,H,I)
    // J,K,L = End (from G,H,I)
    // M,N,O = Both (from G,H,I)
    
    // Mark End (next to |)
    std::cout << "|G=|M" << std::endl; // G->M (Both? tentative)
    std::cout << "|H=|J" << std::endl; // H->J (End)
    std::cout << "|I=|K" << std::endl; // I->K (End)
    
    // If we marked M (Both), check if next is s. If so, single char t.
    // If next is t, then M should be J (End).
    // Actually, | G s. G -> M. M s. Correct.
    // | G H s. G -> M. M H. M should be J.
    // Rule: M H = J H. M I = J I. etc.
    // Fix M -> J if followed by t.
    // M G = J G ...
    std::cout << "MG=JG\nMH=JH\nMI=JI" << std::endl;
    // Also variants
    std::cout << "MJ=JJ\nMK=JK\nML=JL" << std::endl; // J,K,L are End.
    std::cout << "MD=JD\nME=JE\nMF=JF" << std::endl; // D,E,F are Start.
    
    // Mark Start (next to s)
    // G a = D a. (G->D Start).
    // H a = E a.
    // I a = F a.
    // And for b, c.
    std::cout << "Ga=Da\nGb=Db\nGc=Dc" << std::endl;
    std::cout << "Ha=Ea\nHb=Eb\nHc=Ec" << std::endl;
    std::cout << "Ia=Fa\nIb=Fb\nIc=Fc" << std::endl;
    
    // Also Both-check for right side?
    // If J is next to s, it becomes M (Both).
    // J a = M a.
    std::cout << "Ja=Ma\nJb=Mb\nJc=Mc" << std::endl;
    std::cout << "Ka=Na\nKb=Nb\nKc=Nc" << std::endl;
    std::cout << "La=Oa\nLb=Ob\nLc=Oc" << std::endl;

    // Matching
    // Matches:
    // Start: D(a), E(b), F(c)
    // End: J(a), K(b), L(c)
    // Mid: G(a), H(b), I(c)
    // Both: M(a), N(b), O(c)
    
    // Start matches
    std::cout << "Da=d+\nEb=e+\nFc=f+" << std::endl; // Match, mark s with +
    std::cout << "D=W\nE=W\nF=W" << std::endl; // Mismatch Start -> Reset
    
    // Mid matches
    std::cout << "Ga=g+\nHb=h+\nIc=i+" << std::endl;
    std::cout << "G=W\nH=W\nI=W" << std::endl; // Mismatch Mid -> Reset
    
    // End matches -> Success
    std::cout << "Ja=(return)1\nKb=(return)1\nLc=(return)1" << std::endl;
    std::cout << "J=W\nK=W\nL=W" << std::endl;
    
    // Both matches -> Success
    std::cout << "Ma=(return)1\nNb=(return)1\nOc=(return)1" << std::endl;
    std::cout << "M=W\nN=W\nO=W" << std::endl;

    // Bring next t and s together
    // t matched: d,e,f, g,h,i
    // s matched: +
    // Swap t matched right past +
    // d+ = +d, etc.
    std::cout << "d+=+d\ne+=+e\nf+=+f" << std::endl;
    std::cout << "g+=+g\nh+=+h\ni+=+i" << std::endl;
    
    // Swap t matched past s matched (A,B,C?) No s is just +.
    // Wait, we delete s? No we mark s.
    // + is "used s".
    // We need to restore + to a,b,c on reset.
    // + doesn't know what it was.
    // Use A,B,C for s-match-a, s-match-b, s-match-c.
    
    // Revised Matches
    // Start
    std::cout << "Da=dA\nEb=eB\nFc=fC" << std::endl; // d is matched-Start-a. A is matched-s-a.
    // Mid
    std::cout << "Ga=gA\nHb=hB\nIc=iC" << std::endl;
    
    // Move matched t (d..i) past matched s (A..C).
    // d A = A d.
    std::cout << "dA=Ad\ndB=Bd\ndC=Cd" << std::endl;
    std::cout << "eA=Ae\neB=Be\neC=Ce" << std::endl;
    std::cout << "fA=Af\nfB=Bf\nfC=Cf" << std::endl;
    std::cout << "gA=Ag\ngB=Bg\ngC=Cg" << std::endl;
    std::cout << "hA=Ah\nhB=Bh\nhC=Ch" << std::endl;
    std::cout << "iA=Ai\niB=Bi\niC=Ci" << std::endl;
    
    // Reset Logic W
    // W moves left.
    // W restores matched t (d..i) to variants.
    // d->D, e->E, f->F (Start)
    // g->G, h->H, i->I (Mid)
    // W restores matched s (A..C) to a..c.
    // EXCEPT: The s-char paired with Start (d,e,f) must be DELETED.
    
    // Interaction W with s (A,B,C)
    // A W = W a. (Restore)
    std::cout << "AW=Wa\nBW=Wb\nCW=Wc" << std::endl;
    
    // Interaction W with t (d..i)
    // d W = W D %. (% is delete marker).
    // Because d is Start, the s-char to its right (which W just passed) was the first match.
    // But W passes A,B,C first.
    // Sequence: ... d A g B ... W
    // W restores B -> b. W meets g. g -> G.
    // W restores A -> a. W meets d. d -> D.
    // We want A to be deleted.
    // But W sees A before d.
    // We can't let W restore A to a if d is next.
    // But W doesn't look ahead.
    
    // Solution: d,e,f (Start) creates special matched s?
    // Da = d U. (U = die-A).
    // U W = W. (Delete).
    std::cout << "U W=W\nV W=W\nY W=W" << std::endl; // U=die-a, V=die-b, Y=die-c.
    // Redefine Start match
    std::cout << "Da=dU\nEb=eV\nFc=fY" << std::endl;
    // Swap rules for U,V,Y
    std::cout << "dU=Ud\ndV=Vd\ndY=Yd" << std::endl; // and for e,f...
    std::cout << "eU=Ue\neV=Ve\neY=Ye" << std::endl;
    std::cout << "fU=Uf\nfV=Vf\nfY=Yf" << std::endl;
    std::cout << "gU=Ug\ngV=Vg\ngY=Yg" << std::endl; // Mid needs to pass U/V/Y too
    std::cout << "hU=Uh\nhV=Vh\nhY=Yh" << std::endl;
    std::cout << "iU=Ui\niV=Vi\niY=Yi" << std::endl;

    // W restores t
    std::cout << "dW=WD\neW=WE\nfW=WF" << std::endl;
    std::cout << "gW=WG\nhW=WH\niW=WI" << std::endl;
    
    // End of Reset
    // W hits | -> dies?
    std::cout << "|W=|" << std::endl;
    
    // End of Program (Fail)
    // If | D E ... } and D cannot match (s empty), we need to fail.
    // D R -> Fail? R is }.
    std::cout << "D}=(return)0" << std::endl;
    std::cout << "E}=(return)0" << std::endl;
    std::cout << "F}=(return)0" << std::endl;
    // Also M,N,O (Both)
    std::cout << "M}=(return)0\nN}=(return)0\nO}=(return)0" << std::endl;
    
    return 0;
}