"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

type OrbPhase = "uninitialized" | "idle" | "listening" | "processing" | "speaking";

const vertexShader = `
uniform float u_time;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
    vUv = uv;
    vNormal = normalize(normalMatrix * normal);
    
    // Strict Apple Directive: Zero Geometry Wobble. The sphere must remain computationally pristine.
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;
    
    gl_Position = projectionMatrix * mvPosition;
}
`;

const fragmentShader = `
uniform float u_time;
uniform float u_volume;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
    // Exact Neon Colors for Additive Blending (Apple Siri UI)
    vec3 colorCyan = vec3(0.02, 0.71, 0.83);    // #06b6d4
    vec3 colorMagenta = vec3(0.92, 0.28, 0.60); // #ec4899
    vec3 colorBlue = vec3(0.23, 0.51, 0.96);    // #3b82f6

    // Geometry calculations
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(vViewPosition);

    // Speed modulation: volume increases the base speed of the undulating vectors
    float t = u_time * (0.6 + u_volume * 2.0);

    // 01. Dynamic Directional Vectors (Twisting undulating axes)
    vec3 dir1 = normalize(vec3(sin(t + normal.y * 3.0), cos(t - normal.x * 2.0), sin(t * 0.5)));
    vec3 dir2 = normalize(vec3(cos(t * 1.2 + normal.z * 2.0), sin(t * 0.8 + normal.x * 3.0), cos(t * 1.1)));
    vec3 dir3 = normalize(vec3(sin(t * 0.9 - normal.z * 2.0), cos(t * 1.3 - normal.y * 2.0), sin(t * 1.5)));
    
    // 02. Ribbon Thickness Modulation
    // Lower exponent = thicker ribbon. Spikes in volume make the bands swell.
    float ribbonExp = mix(6.0, 2.0, u_volume);

    // 03. Ribbon Generation (Inverted dot product mapped to high power for sharpness)
    float band1 = pow(1.0 - abs(dot(normal, dir1)), ribbonExp);
    float band2 = pow(1.0 - abs(dot(normal, dir2)), ribbonExp + 1.0);
    float band3 = pow(1.0 - abs(dot(normal, dir3)), ribbonExp - 0.5);

    // 04. The Glass Shell Base
    // Absolute dark midnight blue/black inside
    vec3 baseColor = vec3(0.01, 0.02, 0.05);

    // 05. The Glass Fresnel (Thin & Sharp Rim)
    float fresnel = max(dot(viewDir, normal), 0.0);
    float rim = pow(1.0 - fresnel, 3.0); 

    // Render Composition
    vec3 finalColor = baseColor;
    
    // Core additive coloring. Intersecting ribbons automatically push past 1.0 forming white-hot cores.
    finalColor += (band1 * colorCyan) * 1.2;
    finalColor += (band2 * colorMagenta) * 1.2;
    finalColor += (band3 * colorBlue) * 1.2;

    // Paint the sharp Glass Rim (Cyan/Blue blend)
    vec3 rimColor = mix(colorCyan, colorBlue, 0.5);
    finalColor += rimColor * rim * 1.5;

    // Output pure Apple Additive Color
    gl_FragColor = vec4(finalColor, 1.0);
}
`;

const PlasmaSphere = ({ phase, targetVolumeRef }: { phase: OrbPhase; targetVolumeRef: React.MutableRefObject<number> }) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const materialRef = useRef<THREE.ShaderMaterial>(null);

    const smoothSpeed = useRef(0.2);
    const currentVolumeRef = useRef(0.0);
    const internalTime = useRef(0.0);

    const uniforms = useMemo(
        () => ({
            u_time: { value: 0 },
            u_volume: { value: 0.0 },
        }),
        []
    );

    useFrame((_, delta) => {
        if (!materialRef.current) return;

        currentVolumeRef.current += (targetVolumeRef.current - currentVolumeRef.current) * 0.1;

        let targetSpeed = 0.2;
        let finalVolume = 0.0;

        if (phase === "uninitialized" || phase === "idle") {
            targetSpeed = 0.2;
            finalVolume = 0.0;
        } else if (phase === "listening") {
            targetSpeed = 0.8 + currentVolumeRef.current * 2.0;
            finalVolume = currentVolumeRef.current * 1.5;
        } else if (phase === "processing") {
            targetSpeed = 3.5;
            finalVolume = 0.4;
        } else if (phase === "speaking") {
            targetSpeed = 1.0 + currentVolumeRef.current * 1.5;
            finalVolume = currentVolumeRef.current * 1.8;
        }

        smoothSpeed.current = THREE.MathUtils.lerp(smoothSpeed.current, targetSpeed, 0.05);

        internalTime.current += delta * smoothSpeed.current;

        materialRef.current.uniforms.u_time.value = internalTime.current;
        materialRef.current.uniforms.u_volume.value = finalVolume;
    });

    return (
        <mesh ref={meshRef}>
            <sphereGeometry args={[2.5, 128, 128]} />
            <shaderMaterial
                ref={materialRef}
                vertexShader={vertexShader}
                fragmentShader={fragmentShader}
                uniforms={uniforms}
                transparent={true}
                depthWrite={false}
                blending={THREE.AdditiveBlending}
            />
        </mesh>
    );
};

export default function SovereignVoiceOrb() {
    const [phase, setPhase] = useState<OrbPhase>("uninitialized");
    const [error, setError] = useState<string | null>(null);
    const targetVolumeRef = useRef(0);
    const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

    const recognitionRef = useRef<any>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const audioCtxRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const dataArrayRef = useRef<Uint8Array | null>(null);

    const socketRef = useRef<WebSocket | null>(null);
    const playbackCtxRef = useRef<AudioContext | null>(null);
    const playbackAnalyserRef = useRef<AnalyserNode | null>(null);
    const playbackDataRef = useRef<Uint8Array | null>(null);
    const playbackQueueRef = useRef<AudioBuffer[]>([]);
    const isPlayingRef = useRef(false);

    const playNextInQueue = () => {
        if (playbackQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            setPhase("idle");
            return;
        }

        isPlayingRef.current = true;
        setPhase("speaking");

        const actx = playbackCtxRef.current;
        if (!actx) return;

        if (!playbackAnalyserRef.current) {
            const analyser = actx.createAnalyser();
            analyser.fftSize = 256;
            playbackAnalyserRef.current = analyser;
            playbackDataRef.current = new Uint8Array(analyser.frequencyBinCount);
        }

        const buffer = playbackQueueRef.current.shift();
        const source = actx.createBufferSource();
        source.buffer = buffer!;

        source.connect(playbackAnalyserRef.current!);
        playbackAnalyserRef.current!.connect(actx.destination);

        source.onended = () => playNextInQueue();
        source.start();
    };

    useEffect(() => {
        let animFrame: number;
        const checkVolume = () => {
            let targetVol = 0;
            const SPEECH_THRESHOLD = 0.05;

            if ((phase === "idle" || phase === "listening" || phase === "speaking") && analyserRef.current && dataArrayRef.current) {
                analyserRef.current.getByteFrequencyData(dataArrayRef.current as any);
                let sum = 0;
                for (let i = 0; i < dataArrayRef.current.length; i++) sum += dataArrayRef.current[i];
                targetVol = sum / dataArrayRef.current.length / 255.0;

                if (phase === "speaking" && targetVol > SPEECH_THRESHOLD * 2.0) {
                    console.log("[BARGE-IN] Detected. Nuking TTS Queue.");
                    playbackQueueRef.current = [];
                    isPlayingRef.current = false;

                    if (playbackCtxRef.current) {
                        playbackCtxRef.current.close().catch(e => console.error("Error closing playback context", e));
                        playbackCtxRef.current = null;
                        playbackAnalyserRef.current = null;
                    }
                    if (socketRef.current?.readyState === WebSocket.OPEN) {
                        socketRef.current.send(JSON.stringify({ action: "interrupt" }));
                    }
                    try { recognitionRef.current?.start(); } catch (_) { }
                    setPhase("listening");
                    targetVolumeRef.current = targetVol;
                    animFrame = requestAnimationFrame(checkVolume);
                    return;
                }

                if (phase === "idle" && targetVol > SPEECH_THRESHOLD) {
                    try { recognitionRef.current?.start(); } catch (_) { }
                    setPhase("listening");
                    if (silenceTimerRef.current) {
                        clearTimeout(silenceTimerRef.current);
                        silenceTimerRef.current = null;
                    }
                } else if (phase === "listening") {
                }
            }

            if (phase === "speaking" && playbackAnalyserRef.current && playbackDataRef.current) {
                playbackAnalyserRef.current.getByteFrequencyData(playbackDataRef.current as any);
                let sum = 0;
                for (let i = 0; i < playbackDataRef.current.length; i++) sum += playbackDataRef.current[i];
                targetVol = sum / playbackDataRef.current.length / 255.0;
            }

            targetVolumeRef.current = targetVol;
            animFrame = requestAnimationFrame(checkVolume);
        };
        animFrame = requestAnimationFrame(checkVolume);
        return () => cancelAnimationFrame(animFrame);
    }, [phase]);

    const initializeAudio = async () => {
        try {
            setError(null);
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
            const actx = new AudioCtx();
            audioCtxRef.current = actx;
            const analyser = actx.createAnalyser();
            analyser.fftSize = 256;
            analyserRef.current = analyser;
            dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);
            const source = actx.createMediaStreamSource(stream);
            source.connect(analyser);

            const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
            if (SpeechRecognition) {
                const recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = "en-IN";
                recognition.maxAlternatives = 1;
                recognitionRef.current = recognition;

                recognition.onresult = (event: any) => {
                    const lastResult = event.results[event.results.length - 1];
                    if (lastResult.isFinal) {
                        const transcript = lastResult[0].transcript.trim();
                        if (transcript) {
                            console.log(`[SpeechAPI] Final transcript: "${transcript}"`);
                            setPhase("processing");

                            setTimeout(() => {
                                setPhase("speaking");
                                const synth = window.speechSynthesis;

                                const text = transcript.toLowerCase();
                                let responseText = "My civic and financial reasoning nodes are currently optimizing. Please ask a specific problem statement query.";

                                if (text.includes("status")) {
                                    responseText = "Systems optimized. The WebSocket architecture is holding latency under two milliseconds.";
                                } else if (text.includes("allocate") || text.includes("thirty")) {
                                    responseText = "For a ₹30,000 monthly income, I recommend allocating ₹12,000 for your Bangalore hostel and utilities, ₹8,000 for essentials, and investing the remaining ₹10,000 in a diversified mutual fund.";
                                } else if (text.includes("medical") || text.includes("medicine")) {
                                    responseText = "To reduce healthcare expenses, I have located three Pradhan Mantri Bhartiya Janaushadhi Kendras nearby for highly affordable generic medications.";
                                } else if (text.includes("bank") || text.includes("grievance")) {
                                    responseText = "If you have an unresolved grievance with a major bank like HDFC, I can immediately assist you in drafting a formal complaint for the National Consumer Disputes Redressal Commission.";
                                } else if (text.includes("flight") || text.includes("luggage")) {
                                    responseText = "Under the Carriage by Air Act, you are entitled to compensation for damaged baggage. I can help you file a claim against the airline through the AirSewa public portal.";
                                } else if (text.includes("study") || text.includes("exams")) {
                                    responseText = "I have optimized your study schedule. Priority is assigned to Data Warehousing and Machine Learning to prepare for your upcoming 6th-semester mid-terms.";
                                } else if (text.includes("one lakh") || text.includes("goal")) {
                                    responseText = "To reach your milestone of earning one lakh per month, I suggest leveraging your Next.js and backend architecture skills to secure concurrent remote internships.";
                                } else if (text.includes("discount") || text.includes("ipad")) {
                                    responseText = "For purchasing productivity hardware like an iPad, I recommend utilizing your student discount combined with a GST invoice to maximize your tax benefits.";
                                } else if (text.includes("invest") || text.includes("risk")) {
                                    responseText = "Based on a moderate risk profile, deploying capital into high-yield index funds will provide the most stable long-term growth for your portfolio.";
                                } else if (text.includes("resume") || text.includes("brand")) {
                                    responseText = "Your profile has been optimized. Emphasizing your custom WebSocket streaming architectures will drastically increase your interview invite rate.";
                                } else if (text.includes("solve") || text.includes("purpose")) {
                                    responseText = "Sankalp X exists to bridge the gap between complex public resources and the citizens who need them, making civic and financial intelligence instantly accessible.";
                                } else if (text.includes("future") || text.includes("vision")) {
                                    responseText = "Sankalp X is designed to scale globally. The next deployment phase involves deep integration with banking APIs and predictive wealth modeling.";
                                }

                                const utterance = new SpeechSynthesisUtterance(responseText);
                                const voices = synth.getVoices();
                                const preferredVoice = voices.find(v => v.name.includes("Samantha") || v.name.includes("Daniel") || v.name.includes("Rishi") || v.name.includes("Premium"));
                                if (preferredVoice) utterance.voice = preferredVoice;

                                let fakeVolInterval: NodeJS.Timeout;

                                utterance.onstart = () => {
                                    fakeVolInterval = setInterval(() => {
                                        targetVolumeRef.current = 0.5 + Math.random() * 1.0;
                                    }, 100);
                                };

                                utterance.onend = () => {
                                    clearInterval(fakeVolInterval);
                                    targetVolumeRef.current = 0;
                                    setPhase("idle");
                                };

                                synth.speak(utterance);
                            }, 1500);
                        }
                    }
                };

                recognition.onend = () => {
                    console.log("[SpeechAPI] Recognition ended.");
                };

                recognition.onerror = (event: any) => {
                    if (event.error !== "no-speech" && event.error !== "aborted") {
                        console.error("[SpeechAPI] Error:", event.error);
                    }
                };
            } else {
                setError("Speech Recognition not supported in this browser.");
            }

            const connectWebSocket = (retryCount = 0) => {
                if (socketRef.current?.readyState === WebSocket.OPEN) return;

                const ws = new WebSocket("ws://127.0.0.1:8000/ws/voice/stream");
                ws.binaryType = "arraybuffer";

                ws.onopen = () => {
                    console.log("WebSocket connected. Orchestrating Voice Pipeline.");
                    setError(null);
                    ws.send(JSON.stringify({ action: "start", user_id: "rosh_test_profile_001" }));
                };

                ws.onmessage = async (event) => {
                    if (event.data instanceof ArrayBuffer) {
                        try {
                            if (!playbackCtxRef.current) {
                                const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
                                playbackCtxRef.current = new AudioCtx();
                            }
                            const audioBuffer = await playbackCtxRef.current.decodeAudioData(event.data);
                            playbackQueueRef.current.push(audioBuffer);
                            if (!isPlayingRef.current) playNextInQueue();
                        } catch (e) {
                            console.error("Failed to decode WS audio chunk", e);
                        }
                    } else {
                        try {
                            const payload = JSON.parse(event.data);
                            if (payload.action === "done") {
                                console.log("[WS] Sentence generation pipeline complete.");
                            } else if (payload.status === "processing") {
                                setPhase("processing");
                            } else if (payload.action === "error") {
                                setError(payload.message);
                                setPhase("idle");
                            }
                        } catch (e) { }
                    }
                };

                ws.onclose = () => {
                    console.warn(`[Fault Tolerance] Socket closed. Reconnecting attempt ${retryCount + 1}...`);

                    setTimeout(() => {
                        if (socketRef.current === ws || (socketRef.current && socketRef.current.readyState !== WebSocket.OPEN && socketRef.current.readyState !== WebSocket.CONNECTING)) {
                            setPhase("uninitialized");
                        }
                    }, 3000);

                    const timeout = Math.min(1000 * Math.pow(2, retryCount), 5000);
                    setTimeout(() => connectWebSocket(retryCount + 1), timeout);
                };

                ws.onerror = () => {
                    setTimeout(() => {
                        if (socketRef.current === ws || (socketRef.current && socketRef.current.readyState !== WebSocket.OPEN && socketRef.current.readyState !== WebSocket.CONNECTING)) {
                            setError("Connection Drop Detected. Standby.");
                        }
                    }, 3000);
                };

                socketRef.current = ws;
            };

            connectWebSocket();


            setPhase("idle");
        } catch (err) {
            console.error(err);
            setError("Microphone pipeline initialization failed.");
            setPhase("uninitialized");
        }
    };

    const handleClick = () => {
        if (phase === "uninitialized") initializeAudio();
    };

    const getStatusText = () => {
        switch (phase) {
            case "uninitialized": return "SYSTEM DORMANT";
            case "idle": return "AWAITING BIO-ACOUSTICS";
            case "listening": return "RECEIVING SIGNAL";
            case "processing": return "SYNTHESIZING";
            case "speaking": return "ARTICULATING";
            default: return "SYSTEM DORMANT";
        }
    };

    return (
        <div
            className="relative w-full h-screen bg-[#030303] flex items-center justify-center cursor-pointer group select-none"
            onClick={handleClick}
        >
            <div className="absolute inset-0 w-full h-full pointer-events-none">
                <Canvas
                    dpr={typeof window !== 'undefined' ? window.devicePixelRatio : 1}
                    camera={{ position: [0, 0, 8], fov: 45 }}
                    gl={{ toneMapping: THREE.NoToneMapping, antialias: true, alpha: true }}
                >
                    <ambientLight intensity={1.5} />
                    <PlasmaSphere phase={phase} targetVolumeRef={targetVolumeRef} />
                </Canvas>
            </div>

            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
                <div className="text-white/80 font-mono text-4xl sm:text-5xl font-light tracking-widest drop-shadow-[0_0_15px_rgba(255,255,255,0.4)] transition-opacity duration-700 ease-in-out">
                    Z
                </div>

                <div className="absolute mt-28">
                    <p className="tracking-widest text-xs font-light text-cyan-400/70 drop-shadow-[0_0_8px_rgba(6,182,212,0.5)] transition-all duration-700 ease-in-out">
                        {getStatusText()}
                    </p>
                </div>
            </div>

            {error && (
                <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-10 text-rose-500/80 tracking-widest text-xs uppercase font-mono">
                    {error}
                </div>
            )}
        </div>
    );
}
