<script lang="ts">
	let { size = 32 }: { size?: number } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 512 512"
	fill="none"
	xmlns="http://www.w3.org/2000/svg"
	class="logo"
>
	<defs>
		<linearGradient id="nightSky" x1="0%" y1="0%" x2="0%" y2="100%">
			<stop offset="0%" style="stop-color:#0F172A" />
			<stop offset="50%" style="stop-color:#1E293B" />
			<stop offset="100%" style="stop-color:#334155" />
		</linearGradient>
		<linearGradient id="mountain" x1="0%" y1="0%" x2="0%" y2="100%">
			<stop offset="0%" style="stop-color:#475569" />
			<stop offset="100%" style="stop-color:#1E293B" />
		</linearGradient>
		<linearGradient id="forestBack" x1="0%" y1="0%" x2="0%" y2="100%">
			<stop offset="0%" style="stop-color:#14532D" />
			<stop offset="100%" style="stop-color:#052E16" />
		</linearGradient>
		<linearGradient id="forestMid" x1="0%" y1="0%" x2="0%" y2="100%">
			<stop offset="0%" style="stop-color:#166534" />
			<stop offset="100%" style="stop-color:#14532D" />
		</linearGradient>
		<linearGradient id="forestFront" x1="0%" y1="0%" x2="0%" y2="100%">
			<stop offset="0%" style="stop-color:#22C55E" />
			<stop offset="100%" style="stop-color:#16A34A" />
		</linearGradient>
		<linearGradient id="pathGrad" x1="0%" y1="0%" x2="0%" y2="100%">
			<stop offset="0%" style="stop-color:#FCD34D" />
			<stop offset="100%" style="stop-color:#B45309" />
		</linearGradient>
		<linearGradient id="saturn" x1="0%" y1="0%" x2="100%" y2="100%">
			<stop offset="0%" style="stop-color:#F59E0B" />
			<stop offset="100%" style="stop-color:#D97706" />
		</linearGradient>
		<linearGradient id="dragon" x1="0%" y1="0%" x2="0%" y2="100%">
			<stop offset="0%" style="stop-color:#DC2626" />
			<stop offset="100%" style="stop-color:#7F1D1D" />
		</linearGradient>
		<clipPath id="circleClip">
			<circle cx="256" cy="256" r="250" />
		</clipPath>
		<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
			<feGaussianBlur stdDeviation="2" result="coloredBlur"/>
			<feMerge>
				<feMergeNode in="coloredBlur"/>
				<feMergeNode in="SourceGraphic"/>
			</feMerge>
		</filter>
	</defs>

	<circle cx="256" cy="256" r="250" fill="url(#nightSky)" />

	<g clip-path="url(#circleClip)">
		<circle cx="80" cy="60" r="2" fill="#FEFCE8" filter="url(#glow)" />
		<circle cx="150" cy="40" r="1.5" fill="#FEFCE8" filter="url(#glow)" />
		<circle cx="200" cy="80" r="1" fill="#FEF9C3" />
		<circle cx="320" cy="50" r="2" fill="#FEFCE8" filter="url(#glow)" />
		<circle cx="400" cy="70" r="1.5" fill="#FEFCE8" filter="url(#glow)" />
		<circle cx="450" cy="45" r="1" fill="#FEF9C3" />
		<circle cx="100" cy="120" r="1" fill="#FEF9C3" />
		<circle cx="60" cy="150" r="1" fill="#FEF9C3" />
		<circle cx="250" cy="30" r="1.5" fill="#FEFCE8" filter="url(#glow)" />
		<circle cx="130" cy="85" r="2" fill="#FEFCE8" filter="url(#glow)" />

		<ellipse cx="400" cy="100" rx="45" ry="35" fill="url(#saturn)" />
		<ellipse cx="400" cy="100" rx="70" ry="15" fill="none" stroke="#FCD34D" stroke-width="4" opacity="0.7" />
		<ellipse cx="400" cy="100" rx="60" ry="12" fill="none" stroke="#FBBF24" stroke-width="2" opacity="0.5" />

		<polygon points="256,120 380,320 132,320" fill="url(#mountain)" />
		<polygon points="256,120 290,170 222,170" fill="#E2E8F0" />
		<polygon points="256,120 275,155 237,155" fill="#F8FAFC" />
		<polygon points="150,180 250,320 50,320" fill="#334155" />
		<polygon points="380,200 480,320 280,320" fill="#334155" />

		<g fill="url(#dragon)">
			<ellipse cx="320" cy="200" rx="35" ry="20" />
			<path d="M340,190 Q360,170 370,175 Q375,180 370,185 Q365,190 355,195 Q345,195 340,190" />
			<circle cx="367" cy="178" r="3" fill="#FCD34D" />
			<path d="M372,172 L378,162 L374,174" fill="#7F1D1D" />
			<path d="M368,170 L372,158 L370,172" fill="#7F1D1D" />
			<path d="M300,195 Q280,160 290,150 Q300,155 310,170 Q315,180 310,195" fill="#991B1B" />
			<path d="M340,195 Q360,165 365,155 Q360,165 350,180 Q345,190 340,195" fill="#991B1B" />
			<path d="M285,200 Q260,210 250,200 Q245,195 250,190 L255,195 Q265,205 285,200" />
			<path d="M372,182 Q385,180 395,185 Q390,182 395,178 Q400,182 410,180" fill="#F59E0B" opacity="0.8" />
		</g>

		<polygon points="0,320 30,220 60,320" fill="url(#forestBack)" />
		<polygon points="40,320 80,200 120,320" fill="#052E16" />
		<polygon points="90,320 130,230 170,320" fill="url(#forestBack)" />
		<polygon points="350,320 390,210 430,320" fill="url(#forestBack)" />
		<polygon points="400,320 440,220 480,320" fill="#052E16" />
		<polygon points="450,320 490,240 530,320" fill="url(#forestBack)" />

		<polygon points="0,360 40,260 80,360" fill="url(#forestMid)" />
		<polygon points="50,360 100,240 150,360" fill="#14532D" />
		<polygon points="110,360 150,280 190,360" fill="url(#forestMid)" />
		<polygon points="320,360 370,250 420,360" fill="url(#forestMid)" />
		<polygon points="380,360 420,270 460,360" fill="#14532D" />
		<polygon points="430,360 470,290 510,360" fill="url(#forestMid)" />

		<ellipse cx="256" cy="520" rx="320" ry="150" fill="#1E3A21" />

		<path d="M256,510 Q200,480 220,440 Q250,400 300,380 Q350,360 320,320 Q290,280 256,260 Q220,240 240,200 Q260,160 256,140" stroke="url(#pathGrad)" stroke-width="28" fill="none" stroke-linecap="round" />
		<path d="M256,510 Q200,480 220,440 Q250,400 300,380 Q350,360 320,320 Q290,280 256,260 Q220,240 240,200 Q260,160 256,140" stroke="#FEF3C7" stroke-width="8" fill="none" stroke-linecap="round" opacity="0.4" />

		<polygon points="-20,400 30,300 80,400" fill="url(#forestFront)" />
		<polygon points="30,420 80,310 130,420" fill="#16A34A" />
		<polygon points="90,440 130,350 170,440" fill="url(#forestFront)" />
		<polygon points="340,400 390,300 440,400" fill="url(#forestFront)" />
		<polygon points="390,420 430,320 470,420" fill="#16A34A" />
		<polygon points="440,440 480,360 520,440" fill="url(#forestFront)" />

		<path d="M256,465 Q240,475 242,495 L270,495 Q272,475 256,465" fill="#4B5563" />
		<circle cx="256" cy="455" r="14" fill="#FBBF24" />
		<path d="M244,448 Q256,438 268,448 Q270,455 268,462 Q256,458 244,462 Q242,455 244,448" fill="#374151" />
		<circle cx="256" cy="456" r="8" fill="#FCD34D" />
		<line x1="275" y1="450" x2="290" y2="510" stroke="#92400E" stroke-width="4" stroke-linecap="round" />
		<circle cx="275" cy="448" r="6" fill="#3B82F6" filter="url(#glow)" />
		<circle cx="275" cy="448" r="3" fill="#93C5FD" />
		<ellipse cx="248" cy="475" rx="8" ry="12" fill="#7C3AED" />
		<line x1="250" y1="492" x2="245" y2="510" stroke="#4B5563" stroke-width="6" stroke-linecap="round" />
		<line x1="262" y1="492" x2="267" y2="510" stroke="#4B5563" stroke-width="6" stroke-linecap="round" />
	</g>

	<circle cx="256" cy="256" r="250" fill="none" stroke="#475569" stroke-width="4" />
</svg>

<style>
	.logo {
		flex-shrink: 0;
	}
</style>
